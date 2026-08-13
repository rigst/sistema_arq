from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from core.factories import criar_empresa_e_usuario
from core.tenancy import VISITOR_GROUP_PREFIX
from crm.models import Cliente
from legal.testing import aceitar_documentos
from obras.models import EtapaObra, Obra
from projetos.models import Projeto
from regulatorio.models import ObrigacaoTecnica
from tarefas.models import Tarefa

from .models import Notificacao
from .services import varrer_empresa, varrer_todas
from .tasks import varrer_alertas_task


class VarreduraTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, nome="Casa", cliente=self.cliente, status="ativo"
        )

    def test_tarefa_atrasada_gera_notificacao_critica(self):
        Tarefa.objects.create(
            empresa=self.grupo,
            titulo="Enviar planta",
            prazo=timezone.localdate() - timedelta(days=2),
            status="aberta",
        )
        varrer_empresa(self.grupo)
        n = Notificacao.objects.get(empresa=self.grupo)
        self.assertEqual(n.nivel, "critico")

    def test_projeto_parado_gera_alerta(self):
        Projeto.objects.filter(pk=self.projeto.pk).update(
            ultima_atualizacao=timezone.now() - timedelta(days=30)
        )
        varrer_empresa(self.grupo)
        self.assertTrue(
            Notificacao.objects.filter(chave=f"projeto-parado-{self.projeto.pk}").exists()
        )

    def test_obra_em_desvio_gera_alerta(self):
        obra = Obra.objects.create(empresa=self.grupo, projeto=self.projeto)
        EtapaObra.objects.create(
            empresa=self.grupo,
            obra=obra,
            nome="Estrutura",
            percentual_previsto=80,
            percentual_real=40,
            valor=Decimal("1000"),
        )
        varrer_empresa(self.grupo)
        self.assertTrue(Notificacao.objects.filter(chave=f"obra-desvio-{obra.pk}").exists())

    def test_obrigacao_vencida_gera_critico(self):
        o = ObrigacaoTecnica.objects.create(
            empresa=self.grupo,
            tipo="art",
            status="registrada",
            vencimento=timezone.localdate() - timedelta(days=1),
        )
        varrer_empresa(self.grupo)
        n = Notificacao.objects.get(chave=f"obrigacao-{o.pk}-vencida")
        self.assertEqual(n.nivel, "critico")

    def test_varredura_e_idempotente(self):
        Tarefa.objects.create(
            empresa=self.grupo,
            titulo="X",
            prazo=timezone.localdate() - timedelta(days=1),
            status="aberta",
        )
        varrer_empresa(self.grupo)
        varrer_empresa(self.grupo)
        self.assertEqual(Notificacao.objects.filter(empresa=self.grupo).count(), 1)

    def test_obrigacao_vencendo_gera_alerta(self):
        o = ObrigacaoTecnica.objects.create(
            empresa=self.grupo,
            tipo="art",
            status="registrada",
            vencimento=timezone.localdate() + timedelta(days=2),
        )
        varrer_empresa(self.grupo)
        n = Notificacao.objects.get(chave=f"obrigacao-{o.pk}-vencendo")
        self.assertEqual(n.nivel, "alerta")

    def test_obrigacao_pendente_de_registro_gera_alerta(self):
        o = ObrigacaoTecnica.objects.create(empresa=self.grupo, tipo="art", status="pendente")
        varrer_empresa(self.grupo)
        self.assertTrue(Notificacao.objects.filter(chave=f"obrigacao-{o.pk}-pendente").exists())

    def test_obrigacao_em_dia_nao_gera_nada(self):
        ObrigacaoTecnica.objects.create(
            empresa=self.grupo,
            tipo="art",
            status="registrada",
            vencimento=timezone.localdate() + timedelta(days=365),
        )
        self.assertEqual(varrer_empresa(self.grupo), 0)


class VarrerTodasTests(TestCase):
    def test_varre_empresa_real_e_ignora_grupo_de_visitante(self):
        _user, grupo = criar_empresa_e_usuario(username="titular")
        Tarefa.objects.create(
            empresa=grupo,
            titulo="Prazo estourado",
            prazo=timezone.localdate() - timedelta(days=1),
            status="aberta",
        )
        visitante = Group.objects.create(name=f"{VISITOR_GROUP_PREFIX}fulano")
        Tarefa.objects.create(
            empresa=visitante,
            titulo="Não deve alertar",
            prazo=timezone.localdate() - timedelta(days=1),
            status="aberta",
        )

        self.assertEqual(varrer_todas(), 1)
        self.assertFalse(Notificacao.objects.filter(empresa=visitante).exists())

    def test_task_do_celery_delega_para_varrer_todas(self):
        self.assertEqual(varrer_alertas_task(), 0)

    def test_comando_de_gestao_roda_a_varredura(self):
        saida = StringIO()
        call_command("varrer_alertas", stdout=saida)
        self.assertIn("Varredura concluída", saida.getvalue())


class NotificacaoViewTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.client = Client(SERVER_NAME="localhost")
        self.client.force_login(self.user)
        aceitar_documentos(self.user)

    def _nova(self, **kwargs):
        return Notificacao.objects.create(
            empresa=self.grupo, chave="k", titulo="T", mensagem="M", **kwargs
        )

    def test_lista_200(self):
        self._nova()
        resp = self.client.get("/notificacoes/")
        self.assertEqual(resp.status_code, 200)

    def test_marcar_lida_volta_para_a_lista(self):
        n = self._nova()
        resp = self.client.post(f"/notificacoes/{n.pk}/lida/")
        self.assertRedirects(resp, "/notificacoes/")
        n.refresh_from_db()
        self.assertTrue(n.lida)

    def test_marcar_lida_com_url_leva_ao_destino(self):
        n = self._nova(url="/projetos/")
        resp = self.client.post(f"/notificacoes/{n.pk}/lida/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/projetos/")

    def test_marcar_todas(self):
        self._nova()
        Notificacao.objects.create(empresa=self.grupo, chave="k2", titulo="T2", mensagem="M2")
        resp = self.client.post("/notificacoes/todas/")
        self.assertRedirects(resp, "/notificacoes/")
        self.assertEqual(Notificacao.objects.filter(lida=False).count(), 0)

    def test_lista_recusa_post(self):
        self.assertEqual(self.client.post("/notificacoes/").status_code, 405)
