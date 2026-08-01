from decimal import Decimal

from django.test import Client, TestCase

from core.factories import criar_empresa_e_usuario
from core.visitante_cleanup import limpar_dados_negocio
from crm.models import Cliente
from notificacoes.models import Notificacao
from obras.models import EtapaObra, Obra
from projetos.models import Projeto
from regulatorio.models import ObrigacaoTecnica
from legal.testing import aceitar_documentos


class DashboardTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.client = Client(SERVER_NAME="localhost")
        self.client.force_login(self.user)
        aceitar_documentos(self.user)

    def test_dashboard_cockpit_renderiza(self):
        cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente")
        projeto = Projeto.objects.create(
            empresa=self.grupo, nome="Casa", cliente=cliente, status="ativo"
        )
        obra = Obra.objects.create(empresa=self.grupo, projeto=projeto)
        EtapaObra.objects.create(
            empresa=self.grupo, obra=obra, nome="Estrutura",
            percentual_previsto=80, percentual_real=30, valor=Decimal("1000"),
        )
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        # KPIs e navegação lateral presentes.
        self.assertContains(resp, "Projetos ativos")
        self.assertContains(resp, "Obras em desvio")
        self.assertContains(resp, "app-side")


class LimpezaVisitanteFase4Tests(TestCase):
    """Garante que obras, regulatório e notificações se registraram na limpeza
    de visitante e que a ordem respeita as FKs PROTECT (Cliente por último)."""

    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()

    def test_limpeza_remove_dados_das_fases_4(self):
        cliente = Cliente.objects.create(empresa=self.grupo, nome="Visitante")
        projeto = Projeto.objects.create(empresa=self.grupo, nome="P", cliente=cliente)
        obra = Obra.objects.create(empresa=self.grupo, projeto=projeto)
        EtapaObra.objects.create(empresa=self.grupo, obra=obra, nome="E", valor=Decimal("1"))
        ObrigacaoTecnica.objects.create(empresa=self.grupo, tipo="art", projeto=projeto)
        Notificacao.objects.create(empresa=self.grupo, titulo="Alerta", chave="x")

        limpar_dados_negocio(self.grupo)

        self.assertFalse(Obra.objects.filter(empresa=self.grupo).exists())
        self.assertFalse(EtapaObra.objects.filter(empresa=self.grupo).exists())
        self.assertFalse(ObrigacaoTecnica.objects.filter(empresa=self.grupo).exists())
        self.assertFalse(Notificacao.objects.filter(empresa=self.grupo).exists())
        self.assertFalse(Cliente.objects.filter(empresa=self.grupo).exists())
