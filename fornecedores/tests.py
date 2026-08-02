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
            "nome": "Marcenaria", "categoria": "marcenaria", "contato": "",
            "telefone": "", "email": "", "site": "", "documento": "", "cidade": "",
            "prazo_medio_dias": "", "avaliacao": "", "ativo": "on", "observacoes": "",
        }
        self.assertRedirects(self.client.post("/fornecedores/novo/", dados), "/fornecedores/")
        fornecedor = Fornecedor.objects.get()
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
