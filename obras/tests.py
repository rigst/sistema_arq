from decimal import Decimal

from django.test import Client, TestCase

from core.factories import criar_empresa_e_usuario
from crm.models import Cliente
from financeiro.models import ContaBancaria, Lancamento
from legal.testing import aceitar_documentos
from projetos.models import Projeto

from .models import EtapaObra, Medicao, Obra
from .services import aprovar_medicao


class ObraModelTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente X")
        self.projeto = Projeto.objects.create(empresa=self.grupo, nome="Casa", cliente=self.cliente)
        self.obra = Obra.objects.create(empresa=self.grupo, projeto=self.projeto)

    def test_avanco_e_desvio_ponderados_por_valor(self):
        EtapaObra.objects.create(
            empresa=self.grupo,
            obra=self.obra,
            nome="Fundação",
            percentual_previsto=100,
            percentual_real=100,
            valor=Decimal("10000"),
        )
        EtapaObra.objects.create(
            empresa=self.grupo,
            obra=self.obra,
            nome="Estrutura",
            percentual_previsto=50,
            percentual_real=10,
            valor=Decimal("10000"),
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
        self.projeto = Projeto.objects.create(empresa=self.grupo, nome="Loft", cliente=self.cliente)
        self.obra = Obra.objects.create(empresa=self.grupo, projeto=self.projeto)
        self.etapa = EtapaObra.objects.create(
            empresa=self.grupo, obra=self.obra, nome="Acabamento", valor=Decimal("5000")
        )
        self.conta = ContaBancaria.objects.create(empresa=self.grupo, nome="Caixa")

    def test_aprovar_medicao_cria_lancamento_previsto(self):
        medicao = Medicao.objects.create(
            empresa=self.grupo,
            etapa=self.etapa,
            percentual_medido=Decimal("40"),
            valor_liberado=Decimal("2000"),
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
            empresa=self.grupo,
            etapa=self.etapa,
            percentual_medido=Decimal("40"),
            valor_liberado=Decimal("2000"),
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
        resp = self.client.post("/obras/nova/", {"projeto": self.projeto.pk, "status": "planejada"})
        self.assertEqual(resp.status_code, 302)
        obra = Obra.objects.get(projeto=self.projeto)
        self.assertEqual(obra.etapas.count(), 6)

    def test_lista_obras_200(self):
        Obra.objects.create(empresa=self.grupo, projeto=self.projeto)
        resp = self.client.get("/obras/")
        self.assertEqual(resp.status_code, 200)

    def test_formulario_de_abertura_abre_em_get(self):
        resp = self.client.get("/obras/nova/")
        self.assertEqual(resp.status_code, 200)

    def test_editar_obra_altera_e_redireciona(self):
        obra = Obra.objects.create(empresa=self.grupo, projeto=self.projeto)
        resp = self.client.get(f"/obras/{obra.pk}/editar/")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(
            f"/obras/{obra.pk}/editar/",
            {"projeto": self.projeto.pk, "status": "andamento", "endereco": "Rua A, 100"},
        )
        self.assertEqual(resp.status_code, 302)
        obra.refresh_from_db()
        self.assertEqual(obra.status, "andamento")
        self.assertEqual(obra.endereco, "Rua A, 100")


class ObraOperacaoViewTests(TestCase):
    """Exercita os endpoints de POST do dia a dia da obra: etapa, avanço,
    visita e medição."""

    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.client = Client(SERVER_NAME="localhost")
        self.client.force_login(self.user)
        aceitar_documentos(self.user)
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente W")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, nome="Ateliê", cliente=self.cliente
        )
        self.obra = Obra.objects.create(empresa=self.grupo, projeto=self.projeto)
        self.etapa = EtapaObra.objects.create(
            empresa=self.grupo, obra=self.obra, nome="Fundação", valor=Decimal("10000")
        )

    def test_detalhe_obra_200(self):
        resp = self.client.get(f"/obras/{self.obra.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_adicionar_etapa_valida(self):
        resp = self.client.post(
            f"/obras/{self.obra.pk}/etapa/",
            {
                "nome": "Cobertura",
                "ordem": 7,
                "percentual_previsto": "0",
                "percentual_real": "0",
                "valor": "0",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(self.obra.etapas.filter(nome="Cobertura").exists())

    def test_adicionar_etapa_sem_nome_nao_cria(self):
        resp = self.client.post(f"/obras/{self.obra.pk}/etapa/", {"ordem": 1})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.obra.etapas.count(), 1)

    def test_atualizar_avanco_limita_entre_0_e_100(self):
        resp = self.client.post(
            f"/obras/etapa/{self.etapa.pk}/avanco/",
            {"percentual_previsto": "150", "percentual_real": "-20"},
        )
        self.assertEqual(resp.status_code, 302)
        self.etapa.refresh_from_db()
        self.assertEqual(self.etapa.percentual_previsto, Decimal("100"))
        self.assertEqual(self.etapa.percentual_real, Decimal("0"))

    def test_atualizar_avanco_com_texto_avisa_em_vez_de_quebrar(self):
        # Decimal("abc") levanta InvalidOperation, que não é ValueError: antes
        # do tratamento correto isto era 500.
        resp = self.client.post(
            f"/obras/etapa/{self.etapa.pk}/avanco/",
            {"percentual_previsto": "abc", "percentual_real": "10"},
        )
        self.assertEqual(resp.status_code, 302)
        self.etapa.refresh_from_db()
        self.assertEqual(self.etapa.percentual_previsto, Decimal("0"))

    def test_registrar_visita_valida(self):
        resp = self.client.post(
            f"/obras/{self.obra.pk}/visita/",
            {"data": "2026-01-15", "verificado": "Conferida a ferragem da sapata."},
        )
        self.assertEqual(resp.status_code, 302)
        visita = self.obra.visitas.get()
        self.assertEqual(visita.responsavel, self.user)

    def test_registrar_visita_sem_verificado_nao_cria(self):
        resp = self.client.post(f"/obras/{self.obra.pk}/visita/", {"data": "2026-01-15"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.obra.visitas.count(), 0)

    def test_registrar_medicao_valida(self):
        resp = self.client.post(
            f"/obras/{self.obra.pk}/medicao/",
            {
                "etapa": self.etapa.pk,
                "data": "2026-01-20",
                "percentual_medido": "30",
                "valor_liberado": "3000",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Medicao.objects.filter(etapa=self.etapa).count(), 1)

    def test_registrar_medicao_sem_etapa_nao_cria(self):
        resp = self.client.post(
            f"/obras/{self.obra.pk}/medicao/", {"data": "2026-01-20", "percentual_medido": "30"}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Medicao.objects.count(), 0)

    def test_aprovar_medicao_sem_conta_bancaria_avisa(self):
        medicao = Medicao.objects.create(
            empresa=self.grupo, etapa=self.etapa, valor_liberado=Decimal("1000")
        )
        resp = self.client.post(f"/obras/medicao/{medicao.pk}/aprovar/")
        self.assertEqual(resp.status_code, 302)
        medicao.refresh_from_db()
        self.assertFalse(medicao.aprovada)

    def test_aprovar_medicao_com_conta_lanca_no_financeiro(self):
        ContaBancaria.objects.create(empresa=self.grupo, nome="Caixa")
        medicao = Medicao.objects.create(
            empresa=self.grupo, etapa=self.etapa, valor_liberado=Decimal("1000")
        )
        resp = self.client.post(f"/obras/medicao/{medicao.pk}/aprovar/")
        self.assertEqual(resp.status_code, 302)
        medicao.refresh_from_db()
        self.assertTrue(medicao.aprovada)
        self.assertEqual(Lancamento.objects.filter(empresa=self.grupo).count(), 1)
