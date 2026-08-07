from django.test import TestCase

from core.factories import criar_empresa_e_usuario
from fornecedores.models import Fornecedor
from legal.testing import aceitar_documentos


class FornecedoresModalTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        aceitar_documentos(self.user)
        self.client.force_login(self.user)

    def test_lista_expoe_modais_e_crud(self):
        dados = {
            "nome": "Marcenaria",
            "categoria": "marcenaria",
            "contato": "",
            "telefone": "",
            "email": "",
            "site": "",
            "documento": "",
            "cidade": "",
            "prazo_medio_dias": "",
            "avaliacao": "",
            "ativo": "on",
            "observacoes": "",
        }
        self.assertRedirects(self.client.post("/fornecedores/novo/", dados), "/fornecedores/")
        fornecedor = Fornecedor.objects.get()
        self.assertTrue(fornecedor.ativo)
        pagina = self.client.get("/fornecedores/")
        self.assertContains(pagina, "modal-fornecedor-novo")
        self.assertContains(pagina, f"modal-fornecedor-{fornecedor.pk}")
        self.assertContains(pagina, "data-confirmar-exclusao")

        dados["nome"] = "Marcenaria Central"
        self.assertRedirects(
            self.client.post(f"/fornecedores/{fornecedor.pk}/editar/", dados),
            "/fornecedores/",
        )
        fornecedor.refresh_from_db()
        self.assertEqual(fornecedor.nome, "Marcenaria Central")
        self.assertRedirects(
            self.client.post(f"/fornecedores/{fornecedor.pk}/remover/"),
            "/fornecedores/",
        )
        self.assertFalse(Fornecedor.objects.exists())

    def test_fornecedores_inativos_ficam_em_lista_separada(self):
        ativo = Fornecedor.objects.create(
            empresa=self.grupo, nome="Fornecedor ativo", categoria="outro"
        )
        inativo = Fornecedor.objects.create(
            empresa=self.grupo,
            nome="Fornecedor inativo",
            categoria="outro",
            ativo=False,
        )

        pagina_ativos = self.client.get("/fornecedores/")
        self.assertContains(pagina_ativos, ativo.nome)
        self.assertNotContains(pagina_ativos, inativo.nome)
        self.assertContains(pagina_ativos, "Ver fornecedores inativos (1)")

        pagina_inativos = self.client.get("/fornecedores/?inativos=1")
        self.assertContains(pagina_inativos, inativo.nome)
        self.assertNotContains(pagina_inativos, ativo.nome)
        self.assertContains(pagina_inativos, "Voltar aos fornecedores ativos")

    def test_fornecedor_novo_ignora_tentativa_de_criar_inativo(self):
        self.client.post(
            "/fornecedores/novo/",
            {
                "nome": "Novo fornecedor",
                "categoria": "outro",
                "contato": "",
                "telefone": "",
                "email": "",
                "site": "",
                "documento": "",
                "cidade": "",
                "prazo_medio_dias": "",
                "avaliacao": "",
                "ativo": "",
                "observacoes": "",
            },
        )
        self.assertTrue(Fornecedor.objects.get(nome="Novo fornecedor").ativo)
