from decimal import Decimal

from django.test import TestCase

from core.tenancy import obter_grupo_empresa_padrao
from crm.models import Cliente
from fornecedores.models import Fornecedor
from legal.testing import aceitar_documentos
from orcamentos.models import ItemOrcamento, Orcamento
from projetos.models import Projeto
from usuarios.models import Usuario


class OrcamentoTests(TestCase):
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
        self.orcamento = Orcamento.objects.create(
            projeto=self.projeto, empresa=self.grupo, bdi_percent=Decimal("20")
        )

    def _item(self, **kwargs):
        dados = {
            "orcamento": self.orcamento,
            "empresa": self.grupo,
            "descricao": "Item",
            "quantidade": Decimal("1"),
            "valor_unitario": Decimal("1000"),
        }
        dados.update(kwargs)
        return ItemOrcamento.objects.create(**dados)

    def test_total_aplica_bdi_sobre_o_custo_dos_itens(self):
        self._item(quantidade=Decimal("2"), valor_unitario=Decimal("500"))
        self._item(quantidade=Decimal("1"), valor_unitario=Decimal("1500"))
        self.assertEqual(self.orcamento.custo_itens, Decimal("2500.00"))
        self.assertEqual(self.orcamento.valor_bdi, Decimal("500.00"))
        self.assertEqual(self.orcamento.total, Decimal("3000.00"))

    def test_desvio_e_none_ate_alguem_registrar_o_realizado(self):
        self._item()
        self.assertIsNone(self.orcamento.desvio)

    def test_desvio_compara_so_os_itens_ja_contratados(self):
        self._item(valor_unitario=Decimal("1000"), valor_realizado=Decimal("1200"))
        self._item(valor_unitario=Decimal("5000"))  # ainda sem realizado
        self.assertEqual(self.orcamento.desvio, Decimal("200.00"))

    def test_resumo_por_categoria_ordena_do_maior_para_o_menor(self):
        self._item(categoria="marcenaria", valor_unitario=Decimal("9000"))
        self._item(categoria="pintura", valor_unitario=Decimal("1000"))
        resumo = self.orcamento.por_categoria()
        self.assertEqual([linha["rotulo"] for linha in resumo], ["Marcenaria", "Pintura"])

    def test_nova_versao_copia_os_itens_e_encerra_a_anterior(self):
        fornecedor = Fornecedor.objects.create(empresa=self.grupo, nome="Marcenaria Silva")
        self._item(descricao="Armário", fornecedor=fornecedor)

        self.client.get(f"/orcamentos/projeto/{self.projeto.pk}/novo/")

        self.orcamento.refresh_from_db()
        self.assertEqual(self.orcamento.status, "revisado")
        nova = self.projeto.orcamentos.order_by("-criado_em").first()
        self.assertEqual(nova.versao, "2")
        self.assertEqual(nova.itens.count(), 1)
        self.assertEqual(nova.itens.first().fornecedor, fornecedor)
        # O BDI acompanha a versão anterior — reorçar não é redefinir a política.
        self.assertEqual(nova.bdi_percent, Decimal("20"))

    def test_lancar_item_pela_tela(self):
        resposta = self.client.post(
            f"/orcamentos/{self.orcamento.pk}/item/",
            {
                "descricao": "Piso porcelanato",
                "categoria": "revestimento",
                "unidade": "m2",
                "quantidade": "40",
                "valor_unitario": "120",
            },
        )
        self.assertRedirects(resposta, f"/orcamentos/{self.orcamento.pk}/")
        self.assertEqual(self.orcamento.itens.count(), 1)
        self.assertEqual(self.orcamento.custo_itens, Decimal("4800.00"))

    def test_registrar_realizado_aceita_valor_em_formato_brasileiro(self):
        item = self._item()
        self.client.post(f"/orcamentos/item/{item.pk}/realizado/", {"valor_realizado": "1.234,56"})
        item.refresh_from_db()
        self.assertEqual(item.valor_realizado, Decimal("1234.56"))

    def test_limpar_realizado_volta_para_none(self):
        item = self._item(valor_realizado=Decimal("900"))
        self.client.post(f"/orcamentos/item/{item.pk}/realizado/", {"valor_realizado": ""})
        item.refresh_from_db()
        self.assertIsNone(item.valor_realizado)
