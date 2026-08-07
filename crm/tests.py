from django.test import TestCase

from core.factories import criar_empresa_e_usuario
from crm.models import Cliente
from legal.testing import aceitar_documentos
from projetos.models import Projeto


class ClientesModalTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        aceitar_documentos(self.user)
        self.client.force_login(self.user)

    def test_lista_expoe_modais_e_crud(self):
        resposta = self.client.post(
            "/clientes/novo/",
            {"nome": "Ana", "email": "ana@example.com", "origem": "indicacao", "observacoes": ""},
        )
        self.assertRedirects(resposta, "/clientes/")
        cliente = Cliente.objects.get(nome="Ana")
        self.assertTrue(cliente.ativo)

        pagina = self.client.get("/clientes/")
        self.assertContains(pagina, "modal-cliente-novo")
        self.assertContains(pagina, f"modal-cliente-{cliente.pk}")
        self.assertContains(pagina, "data-confirmar-exclusao")

        self.client.post(
            f"/clientes/{cliente.pk}/editar/",
            {
                "nome": "Ana Silva",
                "email": "ana@example.com",
                "telefone": "",
                "origem": "indicacao",
                "fase": "contato",
                "observacoes": "",
                "ativo": "on",
            },
        )
        cliente.refresh_from_db()
        self.assertEqual(cliente.nome, "Ana Silva")
        self.assertRedirects(self.client.post(f"/clientes/{cliente.pk}/remover/"), "/clientes/")
        self.assertFalse(Cliente.objects.exists())

    def test_clientes_inativos_ficam_em_lista_separada(self):
        ativo = Cliente.objects.create(empresa=self.grupo, nome="Cliente ativo")
        inativo = Cliente.objects.create(empresa=self.grupo, nome="Cliente inativo", ativo=False)

        pagina_ativos = self.client.get("/clientes/")
        self.assertContains(pagina_ativos, ativo.nome)
        self.assertNotContains(pagina_ativos, inativo.nome)
        self.assertContains(pagina_ativos, "Ver clientes inativos (1)")

        pagina_inativos = self.client.get("/clientes/?inativos=1")
        self.assertContains(pagina_inativos, inativo.nome)
        self.assertNotContains(pagina_inativos, ativo.nome)
        self.assertContains(pagina_inativos, "Voltar aos clientes ativos")

    def test_cliente_novo_ignora_tentativa_de_criar_inativo(self):
        self.client.post(
            "/clientes/novo/",
            {
                "nome": "Novo cliente",
                "email": "",
                "telefone": "",
                "origem": "outro",
                "observacoes": "",
                "ativo": "",
            },
        )
        self.assertTrue(Cliente.objects.get(nome="Novo cliente").ativo)

    def test_exclusao_de_cliente_com_projeto_e_bloqueada(self):
        cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente com projeto")
        Projeto.objects.create(empresa=self.grupo, cliente=cliente, nome="Casa")
        resposta = self.client.post(f"/clientes/{cliente.pk}/remover/", follow=True)
        self.assertContains(resposta, "não pode ser excluído")
        self.assertTrue(Cliente.objects.filter(pk=cliente.pk).exists())
