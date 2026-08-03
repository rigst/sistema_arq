from django.test import TestCase

from core.tenancy import obter_grupo_empresa_padrao
from financeiro.models import ContaBancaria, Lancamento
from legal.testing import aceitar_documentos
from usuarios.models import Usuario


class PainelFinanceiroTests(TestCase):
    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(
            username="financeiro", password="senha-de-teste"
        )
        self.user.groups.add(self.grupo)
        aceitar_documentos(self.user)
        self.client.force_login(self.user)
        self.conta = ContaBancaria.objects.create(
            empresa=self.grupo, nome="Conta principal", saldo_inicial="1000.00"
        )

    def test_novo_lancamento_fica_em_modal(self):
        resposta = self.client.get("/financeiro/")

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'id="modal-novo-lancamento"')
        self.assertContains(resposta, 'data-abre="modal-novo-lancamento"')

    def test_post_invalido_reabre_modal_com_erros(self):
        resposta = self.client.post("/financeiro/", {"descricao": "Sem valor"})

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "data-modal-inicial")
        self.assertContains(resposta, "Confira os dados do lançamento")

    def test_post_valido_cria_lancamento(self):
        resposta = self.client.post(
            "/financeiro/",
            {
                "tipo": "entrada",
                "conta": self.conta.pk,
                "categoria": "",
                "projeto": "",
                "descricao": "Entrada de contrato",
                "valor": "2500.00",
                "data": "2026-08-02",
                "status": "realizado",
            },
        )

        self.assertRedirects(resposta, "/financeiro/")
        self.assertTrue(
            Lancamento.objects.filter(
                empresa=self.grupo, descricao="Entrada de contrato"
            ).exists()
        )
