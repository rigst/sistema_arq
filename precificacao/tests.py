from decimal import Decimal

from django.test import TestCase

from core.tenancy import obter_grupo_empresa_padrao
from legal.testing import aceitar_documentos
from precificacao.models import ConfiguracaoPrecificacao, CustoFixo, FatorPrecificacao
from precificacao.services import precificar_etapa
from usuarios.models import Usuario


class PrecificacaoTests(TestCase):
    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(username="precificacao", password="senha-de-teste")
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
        self.assertTrue(FatorPrecificacao.objects.get(empresa=self.grupo, nome="Urgência").ativo)

    def test_imposto_e_descontado_da_hora_para_calcular_o_lucro(self):
        ConfiguracaoPrecificacao.objects.update_or_create(
            empresa=self.grupo,
            defaults={
                "hora_tecnica_manual": Decimal("100.00"),
                "margem_seguranca_percent": Decimal("0.00"),
                "imposto_percent": Decimal("6.00"),
            },
        )
        CustoFixo.objects.create(
            empresa=self.grupo, descricao="Operação", valor_mensal=Decimal("1600.00")
        )

        calculo = precificar_etapa(self.grupo, Decimal("1"))
        self.assertEqual(calculo["imposto"], Decimal("6.00"))
        self.assertEqual(calculo["receita_liquida"], Decimal("94.00"))
        self.assertEqual(calculo["custo_operacional"], Decimal("10.00"))
        self.assertEqual(calculo["lucro_previsto"], Decimal("84.00"))
        self.assertEqual(calculo["total"], Decimal("100.00"))

        pagina = self.client.get("/precificacao/")
        self.assertContains(pagina, "Imposto")
        self.assertContains(pagina, "Lucro previsto")
        self.assertNotContains(pagina, "Reserva do escritório")
