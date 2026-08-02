"""Horas do projeto: cronômetro com pausa e lançamento à mão.

A conta de horas alimenta a margem. Um minuto contado a mais em cada pausa,
ou uma hora esquecida rodando a noite inteira, e o custo do projeto passa a
mentir — daí os testes olharem o tempo, não só o fluxo de telas.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.tenancy import obter_grupo_empresa_padrao
from crm.models import Cliente
from legal.testing import aceitar_documentos
from projetos.models import Projeto
from tarefas.models import ApontamentoHora
from usuarios.models import Usuario


class BaseHoras(TestCase):
    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user("horista", password="senha-de-teste")
        self.user.groups.add(self.grupo)
        aceitar_documentos(self.user)
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Marina")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, cliente=self.cliente, nome="Casa Ipê", tipo="residencial"
        )


class CronometroTests(BaseHoras):
    def test_comeca_a_contar_no_projeto(self):
        self.client.post(
            "/tarefas/timer/iniciar/", {"projeto": self.projeto.pk, "descricao": "Planta baixa"}
        )
        aberto = ApontamentoHora.objects.get()
        self.assertTrue(aberto.rodando)
        self.assertEqual(aberto.projeto, self.projeto)
        self.assertEqual(aberto.descricao, "Planta baixa")

    def test_sem_descricao_nao_comeca(self):
        """Registro sem nome vira uma linha de horas que ninguém sabe explicar."""
        self.client.post("/tarefas/timer/iniciar/", {"projeto": self.projeto.pk})
        self.assertFalse(ApontamentoHora.objects.exists())

    def test_comecar_outro_fecha_o_anterior(self):
        for descricao in ["Planta", "Corte"]:
            self.client.post(
                "/tarefas/timer/iniciar/",
                {"projeto": self.projeto.pk, "descricao": descricao},
            )
        abertos = ApontamentoHora.objects.filter(fim__isnull=True)
        self.assertEqual(abertos.count(), 1)
        self.assertEqual(abertos.get().descricao, "Corte")

    def test_pausa_nao_entra_na_conta(self):
        agora = timezone.now()
        ap = ApontamentoHora.objects.create(
            empresa=self.grupo, usuario=self.user, projeto=self.projeto,
            descricao="Detalhe", inicio=agora - timedelta(hours=2),
        )
        # Uma hora rodando, uma hora parada.
        ap.pausado_em = agora - timedelta(hours=1)
        ap.save(update_fields=["pausado_em"])
        ap.parar()
        self.assertTrue(Decimal("0.98") <= ap.horas <= Decimal("1.02"))

    def test_retomar_soma_a_pausa_e_volta_a_andar(self):
        ap = ApontamentoHora.objects.create(
            empresa=self.grupo, usuario=self.user, projeto=self.projeto,
            descricao="Detalhe", inicio=timezone.now() - timedelta(hours=1),
        )
        ap.pausado_em = timezone.now() - timedelta(minutes=30)
        ap.save(update_fields=["pausado_em"])
        ap.retomar()
        self.assertTrue(ap.rodando)
        self.assertGreaterEqual(ap.segundos_pausa, 29 * 60)

    def test_parar_sem_um_minuto_nao_deixa_lixo_na_tabela(self):
        self.client.post(
            "/tarefas/timer/iniciar/", {"projeto": self.projeto.pk, "descricao": "Nada"}
        )
        self.client.post("/tarefas/timer/parar/")
        self.assertFalse(ApontamentoHora.objects.exists())

    def test_o_relogio_aparece_em_qualquer_tela(self):
        self.client.post(
            "/tarefas/timer/iniciar/", {"projeto": self.projeto.pk, "descricao": "Planta baixa"}
        )
        # O painel não tem nada a ver com o projeto e ainda assim mostra.
        self.assertContains(self.client.get("/"), "data-cronometro")


class ApontamentoManualTests(BaseHoras):
    def test_lanca_horas_a_mao(self):
        self.client.post(
            f"/tarefas/horas/projeto/{self.projeto.pk}/",
            {"descricao": "Estudo de layout", "horas": "3.5"},
        )
        ap = ApontamentoHora.objects.get()
        self.assertEqual(ap.horas, Decimal("3.50"))
        self.assertFalse(ap.em_andamento)
        self.assertEqual(self.projeto.horas_trabalhadas, Decimal("3.50"))

    def test_editar_muda_horas_e_descricao(self):
        self.client.post(
            f"/tarefas/horas/projeto/{self.projeto.pk}/",
            {"descricao": "Estudo", "horas": "3.5"},
        )
        ap = ApontamentoHora.objects.get()
        self.client.post(
            f"/tarefas/horas/{ap.pk}/editar/",
            {"descricao": "Estudo revisado", "horas": "4.75"},
        )
        ap.refresh_from_db()
        self.assertEqual(ap.descricao, "Estudo revisado")
        self.assertEqual(ap.horas, Decimal("4.75"))

    def test_nao_corrige_registro_com_cronometro_andando(self):
        self.client.post(
            "/tarefas/timer/iniciar/", {"projeto": self.projeto.pk, "descricao": "Planta"}
        )
        ap = ApontamentoHora.objects.get()
        self.client.post(
            f"/tarefas/horas/{ap.pk}/editar/", {"descricao": "Trapaça", "horas": "40"}
        )
        ap.refresh_from_db()
        self.assertEqual(ap.descricao, "Planta")
        self.assertTrue(ap.em_andamento)

    def test_excluir_tira_da_conta_do_projeto(self):
        self.client.post(
            f"/tarefas/horas/projeto/{self.projeto.pk}/",
            {"descricao": "Estudo", "horas": "3.5"},
        )
        ap = ApontamentoHora.objects.get()
        self.client.post(f"/tarefas/horas/{ap.pk}/remover/")
        self.assertEqual(self.projeto.horas_trabalhadas, Decimal("0"))

    def test_horas_de_outra_empresa_dao_404(self):
        from django.contrib.auth.models import Group

        outro = Group.objects.create(name="Vizinho horas")
        alheio = ApontamentoHora.objects.create(
            empresa=outro, usuario=self.user, descricao="Alheio",
            inicio=timezone.now() - timedelta(hours=1), fim=timezone.now(),
        )
        self.assertEqual(
            self.client.post(f"/tarefas/horas/{alheio.pk}/remover/").status_code, 404
        )
