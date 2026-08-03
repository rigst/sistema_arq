
from django.test import TestCase

from briefing.models import Briefing, RespostaBriefing, TemplateBriefing
from briefing.services import semear_templates_padrao
from briefing.templates_padrao import PADROES
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
        self.assertEqual(len(primeiros), len(PADROES))
        self.assertEqual(semear_templates_padrao(self.grupo, self.user), [])
        self.assertEqual(
            TemplateBriefing.objects.filter(empresa=self.grupo).count(), len(PADROES)
        )

    def test_pagina_de_modelos_recompoe_roteiro_padrao_excluido(self):
        semear_templates_padrao(self.grupo, self.user)
        TemplateBriefing.objects.filter(
            empresa=self.grupo, nome=PADROES[0]["nome"]
        ).delete()

        resposta = self.client.get("/modelos/")

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, PADROES[0]["nome"])
        self.assertContains(resposta, 'id="modal-novo-briefing"')

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

    def test_edicao_de_pergunta_substitui_dados_e_opcoes(self):
        template = semear_templates_padrao(self.grupo, self.user)[0]
        pergunta = template.perguntas.first()

        resposta = self.client.post(
            f"/briefing/pergunta/{pergunta.pk}/editar/",
            {
                "bloco": "Decisão",
                "texto": "Quem aprova cada etapa?",
                "tipo": "opcao",
                "opcoes": "Uma pessoa\nCasal\nComitê",
                "ajuda": "Registre o decisor principal.",
            },
        )

        self.assertRedirects(resposta, f"/briefing/roteiro/{template.pk}/")
        pergunta.refresh_from_db()
        self.assertEqual(pergunta.bloco, "Decisão")
        self.assertEqual(pergunta.texto, "Quem aprova cada etapa?")
        self.assertEqual(
            list(pergunta.opcoes.values_list("texto", flat=True)),
            ["Uma pessoa", "Casal", "Comitê"],
        )

    def test_roteiro_novo_e_sempre_criado_ativo(self):
        resposta = self.client.post(
            "/briefing/roteiro/novo/",
            {
                "nome": "Roteiro próprio",
                "tipo_projeto": "",
                "descricao": "Teste",
                "ativo": "",
            },
        )

        roteiro = TemplateBriefing.objects.get(nome="Roteiro próprio")
        self.assertTrue(roteiro.ativo)
        self.assertRedirects(resposta, f"/briefing/roteiro/{roteiro.pk}/")
