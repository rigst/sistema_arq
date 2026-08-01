from django.contrib.auth.models import Group
from django.test import TestCase

from briefing.models import Briefing, RespostaBriefing
from briefing.services import semear_templates_padrao
from core.tenancy import obter_grupo_empresa_padrao
from crm.models import Cliente
from jornada.roteiro import montar_roteiro, percentual, proxima_etapa
from legal.testing import aceitar_documentos
from orcamentos.models import ItemOrcamento, Orcamento
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

    def test_roteiro_comeca_so_com_o_cliente_pronto(self):
        etapas = montar_roteiro(self.projeto)
        self.assertEqual([e.chave for e in etapas][:3], ["cliente", "briefing", "orcamento"])
        self.assertTrue(etapas[0].concluida)
        self.assertEqual(proxima_etapa(etapas).chave, "briefing")
        self.assertEqual(percentual(etapas), 17)

    def test_briefing_respondido_avanca_o_roteiro(self):
        template = semear_templates_padrao(self.grupo, self.user)[0]
        briefing = Briefing.objects.create(projeto=self.projeto, empresa=self.grupo)
        RespostaBriefing.objects.create(
            briefing=briefing,
            empresa=self.grupo,
            pergunta=template.perguntas.first(),
            texto="Casal com dois filhos",
        )
        etapas = montar_roteiro(self.projeto)
        self.assertTrue(next(e for e in etapas if e.chave == "briefing").concluida)
        self.assertEqual(proxima_etapa(etapas).chave, "orcamento")

    def test_orcamento_so_conta_quando_tem_item(self):
        orcamento = Orcamento.objects.create(projeto=self.projeto, empresa=self.grupo)
        self.assertFalse(next(e for e in montar_roteiro(self.projeto) if e.chave == "orcamento").concluida)

        ItemOrcamento.objects.create(
            orcamento=orcamento,
            empresa=self.grupo,
            descricao="Marcenaria da cozinha",
            quantidade=1,
            valor_unitario=25000,
        )
        self.assertTrue(next(e for e in montar_roteiro(self.projeto) if e.chave == "orcamento").concluida)

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
        self.assertRedirects(resposta, f"/projeto-novo/{projeto.pk}/")
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

    def test_roteiro_de_outra_empresa_da_404(self):
        outro_grupo = Group.objects.create(name="Outro escritório")
        intruso = Usuario.objects.create_user(username="intruso", password="senha-de-teste-2")
        # Todo usuário novo entra na empresa padrão por signal; aqui o intruso
        # precisa pertencer só ao outro escritório.
        intruso.groups.clear()
        intruso.groups.add(outro_grupo)
        self.client.force_login(intruso)
        aceitar_documentos(intruso)
        self.assertEqual(self.client.get(f"/projeto-novo/{self.projeto.pk}/").status_code, 404)
