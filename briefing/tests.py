from unittest import mock

from django.test import TestCase

from briefing.models import Briefing, RespostaBriefing, TemplateBriefing
from briefing.services import respostas_para_ia, semear_templates_padrao
from core.ia import IAIndisponivel
from core.tenancy import obter_grupo_empresa_padrao
from crm.models import Cliente
from legal.testing import aceitar_documentos
from projetos.models import Projeto
from usuarios.models import Usuario


class TemplatesTests(TestCase):
    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(username="arq", password="senha-de-teste-1")
        self.user.groups.add(self.grupo)
        self.client.force_login(self.user)
        aceitar_documentos(self.user)

        cliente = Cliente.objects.create(empresa=self.grupo, nome="Marina")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, cliente=cliente, nome="Residência Ipê"
        )

    def test_semear_padroes_e_idempotente(self):
        primeiros = semear_templates_padrao(self.grupo, self.user)
        self.assertEqual(len(primeiros), 2)
        self.assertEqual(semear_templates_padrao(self.grupo, self.user), [])
        self.assertEqual(TemplateBriefing.objects.filter(empresa=self.grupo).count(), 2)

    def test_padroes_trazem_perguntas_com_opcoes(self):
        template = semear_templates_padrao(self.grupo, self.user)[0]
        primeira = template.perguntas.first()
        self.assertTrue(primeira.opcoes.exists())
        self.assertTrue(primeira.aceita_opcoes)

    def test_responder_grava_opcoes_e_complemento(self):
        template = semear_templates_padrao(self.grupo, self.user)[0]
        pergunta = template.perguntas.filter(tipo="multipla").first()
        opcao = pergunta.opcoes.first()

        self.client.post(f"/briefing/projeto/{self.projeto.pk}/roteiro/", {"template": template.pk})
        self.client.post(
            f"/briefing/projeto/{self.projeto.pk}/responder/",
            {f"p{pergunta.pk}": [str(opcao.pk)], f"t{pergunta.pk}": "Tem um gato"},
        )

        resposta = RespostaBriefing.objects.get(pergunta=pergunta)
        self.assertEqual(list(resposta.opcoes.all()), [opcao])
        self.assertEqual(resposta.texto, "Tem um gato")
        self.assertIn(opcao.texto, resposta.resumo)
        self.assertIn("Tem um gato", resposta.resumo)

    def test_resposta_vazia_e_apagada_em_vez_de_ficar_em_branco(self):
        template = semear_templates_padrao(self.grupo, self.user)[0]
        pergunta = template.perguntas.first()
        briefing = Briefing.objects.create(projeto=self.projeto, empresa=self.grupo)
        RespostaBriefing.objects.create(
            briefing=briefing, empresa=self.grupo, pergunta=pergunta, texto="algo"
        )

        self.client.post(f"/briefing/projeto/{self.projeto.pk}/roteiro/", {"template": template.pk})
        self.client.post(f"/briefing/projeto/{self.projeto.pk}/responder/", {f"t{pergunta.pk}": ""})
        self.assertFalse(RespostaBriefing.objects.filter(pergunta=pergunta).exists())

    def test_respostas_para_ia_ignora_o_que_esta_em_branco(self):
        template = semear_templates_padrao(self.grupo, self.user)[0]
        briefing = Briefing.objects.create(projeto=self.projeto, empresa=self.grupo)
        perguntas = list(template.perguntas.all()[:2])
        RespostaBriefing.objects.create(
            briefing=briefing, empresa=self.grupo, pergunta=perguntas[0], texto="Casal"
        )
        RespostaBriefing.objects.create(
            briefing=briefing, empresa=self.grupo, pergunta=perguntas[1], texto=""
        )
        pares = respostas_para_ia(briefing)
        self.assertEqual(pares, [(perguntas[0].texto, "Casal")])

    def test_pergunta_nova_aceita_opcoes_uma_por_linha(self):
        template = TemplateBriefing.objects.create(empresa=self.grupo, nome="Meu roteiro")
        self.client.post(
            f"/briefing/roteiro/{template.pk}/pergunta/",
            {"texto": "Qual o estilo?", "tipo": "opcao", "opcoes": "Clean\nClássico\n\nRústico"},
        )
        pergunta = template.perguntas.get()
        self.assertEqual(
            [o.texto for o in pergunta.opcoes.all()], ["Clean", "Clássico", "Rústico"]
        )


class LeituraIATests(TestCase):
    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(username="arq", password="senha-de-teste-1")
        self.user.groups.add(self.grupo)
        self.client.force_login(self.user)
        aceitar_documentos(self.user)
        cliente = Cliente.objects.create(empresa=self.grupo, nome="Marina")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, cliente=cliente, nome="Residência Ipê"
        )
        template = semear_templates_padrao(self.grupo, self.user)[0]
        briefing = Briefing.objects.create(projeto=self.projeto, empresa=self.grupo)
        RespostaBriefing.objects.create(
            briefing=briefing,
            empresa=self.grupo,
            pergunta=template.perguntas.first(),
            texto="Casal com dois filhos",
        )

    @mock.patch("briefing.views.resumir_briefing", return_value="Leitura do briefing.")
    def test_leitura_volta_como_rascunho_na_tela(self, _falso):
        self.client.post(f"/briefing/projeto/{self.projeto.pk}/leitura-ia/")
        resposta = self.client.get(f"/briefing/projeto/{self.projeto.pk}/responder/")
        self.assertContains(resposta, "Leitura do briefing.")

    @mock.patch(
        "briefing.views.resumir_briefing",
        side_effect=IAIndisponivel("Apoio de IA desligado."),
    )
    def test_ia_desligada_vira_recado_e_nao_erro(self, _falso):
        resposta = self.client.post(
            f"/briefing/projeto/{self.projeto.pk}/leitura-ia/", follow=True
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Apoio de IA desligado.")
