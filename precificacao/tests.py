from decimal import Decimal

from django.test import TestCase

from core.tenancy import obter_grupo_empresa_padrao
from legal.testing import aceitar_documentos
from precificacao.models import CustoFixo, FatorPrecificacao
from usuarios.models import Usuario


class PrecificacaoTests(TestCase):
    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(
            username="precificacao", password="senha-de-teste"
        )
        self.user.groups.add(self.grupo)
        aceitar_documentos(self.user)
        self.client.force_login(self.user)

    def test_custo_criado_pela_tela_fica_ativo_e_entra_no_calculo(self):
        resposta = self.client.post(
            "/precificacao/custos/adicionar/",
            {"descricao": "Aluguel", "valor_mensal": "1600.00"},
        )

        self.assertRedirects(resposta, "/precificacao/")
        custo = CustoFixo.objects.get(empresa=self.grupo, descricao="Aluguel")
        self.assertTrue(custo.ativo)
        pagina = self.client.get("/precificacao/")
        self.assertEqual(pagina.context["custo_hora"], Decimal("10.00"))

    def test_fator_criado_pela_tela_fica_ativo(self):
        resposta = self.client.post(
            "/precificacao/fatores/adicionar/",
            {"nome": "Urgência", "percentual": "20.00"},
        )

        self.assertRedirects(resposta, "/precificacao/")
        self.assertTrue(
            FatorPrecificacao.objects.get(
                empresa=self.grupo, nome="Urgência"
            ).ativo
        )
