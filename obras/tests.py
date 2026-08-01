from decimal import Decimal

from django.test import Client, TestCase

from core.factories import criar_empresa_e_usuario
from crm.models import Cliente
from financeiro.models import ContaBancaria, Lancamento
from projetos.models import Projeto

from .models import EtapaObra, Medicao, Obra
from .services import aprovar_medicao
from legal.testing import aceitar_documentos


class ObraModelTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente X")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, nome="Casa", cliente=self.cliente
        )
        self.obra = Obra.objects.create(empresa=self.grupo, projeto=self.projeto)

    def test_avanco_e_desvio_ponderados_por_valor(self):
        EtapaObra.objects.create(
            empresa=self.grupo, obra=self.obra, nome="Fundação",
            percentual_previsto=100, percentual_real=100, valor=Decimal("10000"),
        )
        EtapaObra.objects.create(
            empresa=self.grupo, obra=self.obra, nome="Estrutura",
            percentual_previsto=50, percentual_real=10, valor=Decimal("10000"),
        )
        # Previsto: (100*10000 + 50*10000)/20000 = 75; Real: (100+10)/2 => 55
        self.assertEqual(self.obra.avanco_previsto, Decimal("75.0"))
        self.assertEqual(self.obra.avanco_real, Decimal("55.0"))
        self.assertEqual(self.obra.desvio, Decimal("20.0"))
        self.assertTrue(self.obra.em_desvio)

    def test_obra_sem_etapas_nao_esta_em_desvio(self):
        self.assertEqual(self.obra.avanco_previsto, Decimal("0"))
        self.assertFalse(self.obra.em_desvio)


class MedicaoServiceTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente Y")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, nome="Loft", cliente=self.cliente
        )
        self.obra = Obra.objects.create(empresa=self.grupo, projeto=self.projeto)
        self.etapa = EtapaObra.objects.create(
            empresa=self.grupo, obra=self.obra, nome="Acabamento", valor=Decimal("5000")
        )
        self.conta = ContaBancaria.objects.create(empresa=self.grupo, nome="Caixa")

    def test_aprovar_medicao_cria_lancamento_previsto(self):
        medicao = Medicao.objects.create(
            empresa=self.grupo, etapa=self.etapa,
            percentual_medido=Decimal("40"), valor_liberado=Decimal("2000"),
        )
        lanc = aprovar_medicao(medicao, self.conta)
        medicao.refresh_from_db()
        self.assertTrue(medicao.aprovada)
        self.assertIsNotNone(lanc)
        self.assertEqual(lanc.tipo, "entrada")
        self.assertEqual(lanc.status, "previsto")
        self.assertEqual(lanc.valor, Decimal("2000"))
        self.assertEqual(lanc.projeto_id, self.projeto.pk)
        # Puxa o avanço real da etapa.
        self.etapa.refresh_from_db()
        self.assertEqual(self.etapa.percentual_real, Decimal("40"))

    def test_aprovar_medicao_e_idempotente(self):
        medicao = Medicao.objects.create(
            empresa=self.grupo, etapa=self.etapa,
            percentual_medido=Decimal("40"), valor_liberado=Decimal("2000"),
        )
        aprovar_medicao(medicao, self.conta)
        aprovar_medicao(medicao, self.conta)
        self.assertEqual(Lancamento.objects.filter(empresa=self.grupo).count(), 1)


class ObraViewTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.client = Client(SERVER_NAME="localhost")
        self.client.force_login(self.user)
        aceitar_documentos(self.user)
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente Z")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, nome="Studio", cliente=self.cliente
        )

    def test_abrir_obra_cria_etapas_padrao(self):
        resp = self.client.post(
            "/obras/nova/", {"projeto": self.projeto.pk, "status": "planejada"}
        )
        self.assertEqual(resp.status_code, 302)
        obra = Obra.objects.get(projeto=self.projeto)
        self.assertEqual(obra.etapas.count(), 6)

    def test_lista_obras_200(self):
        Obra.objects.create(empresa=self.grupo, projeto=self.projeto)
        resp = self.client.get("/obras/")
        self.assertEqual(resp.status_code, 200)
