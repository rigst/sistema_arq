from django.contrib.auth.models import Group
from django.test import TestCase

from core.tenancy import obter_grupo_empresa_padrao
from crm.models import Cliente
from fases.models import Fase, montar_fases
from jornada.roteiro import montar_roteiro, percentual, proxima_etapa
from legal.testing import aceitar_documentos
from projetos.models import Projeto
from usuarios.models import Usuario


class RoteiroTests(TestCase):
    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(username="arq", password="senha-de-teste-1")
        self.user.groups.add(self.grupo)
        self.client.force_login(self.user)
        aceitar_documentos(self.user)

        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Marina Costa")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, cliente=self.cliente, nome="Residência Ipê"
        )
        montar_fases(self.projeto)

    def test_roteiro_e_a_lista_de_fases_na_ordem(self):
        etapas = montar_roteiro(self.projeto)
        self.assertEqual(
            [e.chave for e in etapas],
            [
                "briefing", "proposta", "contrato", "estudo_preliminar",
                "anteprojeto", "executivo",
            ],
        )
        self.assertEqual(proxima_etapa(etapas).chave, "briefing")
        self.assertEqual(percentual(etapas), 0)

    def test_fase_aprovada_avanca_o_roteiro(self):
        briefing = self.projeto.fases.get(chave="briefing")
        briefing.abrir(self.user)
        briefing.concluir_sem_aprovacao(self.user)
        etapas = montar_roteiro(self.projeto)
        self.assertTrue(etapas[0].concluida)
        self.assertEqual(proxima_etapa(etapas).chave, "proposta")
        self.assertEqual(percentual(etapas), 17)

    def test_proxima_prioriza_a_fase_ja_aberta(self):
        """Uma fase em elaboração pede mais atenção do que a seguinte, que nem
        começou — senão o painel manda o arquiteto começar coisa nova."""
        from fases.models import Fase

        # A ordem é obrigatória, então a anterior precisa estar aprovada.
        anteprojeto = self.projeto.fases.get(chave="anteprojeto")
        self.projeto.fases.filter(ordem__lt=anteprojeto.ordem).update(status=Fase.APROVADA)
        anteprojeto.abrir(self.user)
        self.assertEqual(proxima_etapa(montar_roteiro(self.projeto)).chave, "anteprojeto")

    def test_abrir_cria_cliente_e_projeto_de_uma_vez(self):
        resposta = self.client.post(
            "/projeto-novo/novo/",
            {
                "cliente_nome": "João Pereira",
                "cliente_email": "joao@exemplo.com",
                "nome": "Apartamento Vila Nova",
                "tipo": "residencial",
            },
        )
        projeto = Projeto.objects.get(nome="Apartamento Vila Nova")
        # Depois de criado, o primeiro trabalho real é o briefing.
        self.assertRedirects(
            resposta, f"/briefing/projeto/{projeto.pk}/responder/"
        )
        self.assertEqual(projeto.status, "ativo")
        self.assertEqual(projeto.cliente.nome, "João Pereira")
        self.assertEqual(projeto.empresa, self.grupo)

    def test_abrir_reaproveita_cliente_existente(self):
        self.client.post(
            "/projeto-novo/novo/",
            {
                "cliente_existente": self.cliente.pk,
                "nome": "Segunda obra da Marina",
                "tipo": "residencial",
            },
        )
        self.assertEqual(Cliente.objects.filter(empresa=self.grupo).count(), 1)
        self.assertEqual(self.cliente.projetos.count(), 2)

    def test_abrir_exige_um_cliente(self):
        resposta = self.client.post(
            "/projeto-novo/novo/", {"nome": "Sem cliente", "tipo": "residencial"}
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Projeto.objects.filter(nome="Sem cliente").exists())

    def test_ficha_do_projeto_traz_as_fases(self):
        resposta = self.client.get(f"/projetos/{self.projeto.pk}/")
        self.assertContains(resposta, "Fases do projeto")
        self.assertContains(resposta, "Estudo preliminar")
        # A fase bloqueada não vira link — só a que está aberta.
        aberta = self.projeto.fases.get(chave="briefing")
        self.assertContains(resposta, f"/fases/{aberta.pk}/")
        self.assertContains(resposta, "Bloqueada")

    def test_execucao_so_entra_no_roteiro_quando_o_projeto_tem(self):
        """Muitos trabalhos terminam no projeto entregue; a obra é exceção."""
        chaves = [e.chave for e in montar_roteiro(self.projeto)]
        self.assertNotIn("execucao", chaves)

        self.projeto.tem_execucao = True
        self.projeto.save(update_fields=["tem_execucao"])
        etapas = montar_roteiro(self.projeto)
        self.assertEqual(etapas[-1].chave, "execucao")
        self.assertIn(f"/obras/nova/?projeto={self.projeto.pk}", etapas[-1].url)

    def test_abertura_liga_os_complementares_escolhidos(self):
        self.client.post(
            "/projeto-novo/novo/",
            {
                "cliente_existente": self.cliente.pk,
                "nome": "Casa com estrutural",
                "tipo": "residencial",
                "complementares": ["comp_estrutural"],
            },
        )
        projeto = Projeto.objects.get(nome="Casa com estrutural")
        chaves = list(projeto.fases.values_list("chave", flat=True))
        self.assertIn("comp_estrutural", chaves)
        self.assertNotIn("comp_eletrica", chaves)

    def test_formulario_aberto_do_projeto_ja_vem_preenchido(self):
        """O ganho todo do contexto: não redigitar o que o sistema já sabe."""
        self.projeto.fases.filter(chave__in=("briefing", "proposta")).update(
            status=Fase.APROVADA
        )
        resposta = self.client.get(f"/contratos/novo/?projeto={self.projeto.pk}")
        form = resposta.context["form"]
        self.assertEqual(form.fields["projeto"].initial, self.projeto.pk)
        self.assertTrue(form.fields["projeto"].disabled)
        self.assertIn(self.projeto.nome, form.fields["titulo"].initial)
        self.assertContains(resposta, "Dentro do projeto")

    def test_proposta_criada_do_projeto_fecha_o_laco(self):
        self.projeto.fases.filter(chave="briefing").update(status=Fase.APROVADA)
        fase = self.projeto.fases.get(chave="proposta")
        resposta = self.client.get(f"/fases/{fase.pk}/")
        self.projeto.refresh_from_db()
        proposta = getattr(self.projeto, "proposta_origem", None)
        self.assertIsNotNone(proposta)
        self.assertEqual(proposta.cliente, self.projeto.cliente)
        self.assertRedirects(resposta, f"/propostas/{proposta.pk}/")


    def test_projeto_de_outra_empresa_nao_vira_contexto(self):
        outro_grupo = Group.objects.create(name="Escritório vizinho")
        alheio = Projeto.objects.create(
            empresa=outro_grupo, cliente=self.cliente, nome="Alheio", tipo="residencial"
        )
        resposta = self.client.get(f"/contratos/novo/?projeto={alheio.pk}")
        self.assertNotContains(resposta, "Dentro do projeto")
        self.assertFalse(resposta.context["form"].fields["projeto"].disabled)
