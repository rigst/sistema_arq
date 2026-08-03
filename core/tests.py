from decimal import Decimal
from datetime import date
from datetime import datetime
from unittest.mock import patch

from django.test import Client, TestCase
from django.utils import timezone

from core.factories import criar_empresa_e_usuario
from core.views import FRASES_MOTIVACIONAIS, _primeiro_nome_usuario, _saudacao_do_dia
from core.models import Empresa
from core.pdf import _identidade_pdf, render_pdf
from core.visitante_cleanup import limpar_dados_negocio
from crm.models import Cliente
from briefing.models import TemplateBriefing
from contratos.models import ModeloContrato
from notificacoes.models import Notificacao
from financeiro.models import ContaBancaria, Lancamento
from obras.models import EtapaObra, Obra
from projetos.models import Projeto
from regulatorio.models import ObrigacaoTecnica
from legal.testing import aceitar_documentos
from usuarios.models import Usuario


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
        self.assertContains(resp, "Aguardando cliente")
        self.assertContains(resp, "app-side")

    def test_dashboard_sauda_com_primeiro_nome_e_frase_do_dia(self):
        self.user.nome_exibicao = "Marina Costa"
        self.user.save(update_fields=["nome_exibicao"])
        agora = datetime(2026, 8, 3, 9, 30, tzinfo=timezone.get_current_timezone())
        with patch("core.views.timezone.localtime", return_value=agora):
            resp = self.client.get("/")

        self.assertContains(resp, "Bom dia, Marina.")
        self.assertContains(resp, FRASES_MOTIVACIONAIS[agora.date().toordinal() % len(FRASES_MOTIVACIONAIS)])

    def test_saudacao_muda_por_periodo_e_primeiro_nome_tem_fallback(self):
        self.assertEqual(_saudacao_do_dia(datetime(2026, 8, 3, 11, 59))[0], "Bom dia")
        self.assertEqual(_saudacao_do_dia(datetime(2026, 8, 3, 12, 0))[0], "Boa tarde")
        self.assertEqual(_saudacao_do_dia(datetime(2026, 8, 3, 18, 0))[0], "Boa noite")
        self.user.nome_exibicao = ""
        self.user.first_name = "João"
        self.user.save(update_fields=["nome_exibicao", "first_name"])
        self.assertEqual(_primeiro_nome_usuario(self.user), "João")

    def test_primeiro_acesso_instala_modelos_sem_duplicar(self):
        self.assertFalse(TemplateBriefing.objects.filter(empresa=self.grupo).exists())
        self.assertFalse(ModeloContrato.objects.filter(empresa=self.grupo).exists())

        self.client.get("/")
        quantidade_briefings = TemplateBriefing.objects.filter(empresa=self.grupo).count()
        quantidade_contratos = ModeloContrato.objects.filter(empresa=self.grupo).count()
        self.assertGreaterEqual(quantidade_briefings, 2)
        self.assertGreaterEqual(quantidade_contratos, 2)

        self.client.get("/")
        self.assertEqual(
            TemplateBriefing.objects.filter(empresa=self.grupo).count(), quantidade_briefings
        )
        self.assertEqual(
            ModeloContrato.objects.filter(empresa=self.grupo).count(), quantidade_contratos
        )

    def test_valor_a_receber_usa_decimal_em_portugues(self):
        conta = ContaBancaria.objects.create(empresa=self.grupo, nome="Principal")
        Lancamento.objects.create(
            empresa=self.grupo,
            conta=conta,
            tipo="entrada",
            descricao="Parcela",
            valor=Decimal("950.40"),
            data=date(2026, 8, 5),
            status="previsto",
        )

        resposta = self.client.get("/")
        self.assertContains(resposta, "R$ 950,40")
        self.assertNotContains(resposta, "R$ 950.40")


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


class IdentidadeTests(TestCase):
    """A imagem de fundo do painel é do escritório, não do sistema."""

    def setUp(self):
        from core.tenancy import obter_grupo_empresa_padrao

        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(username="ident", password="senha-de-teste")
        self.user.groups.add(self.grupo)
        aceitar_documentos(self.user)
        self.client.force_login(self.user)

    def _png(self, nome="fundo.png"):
        """Um PNG mínimo de verdade: ImageField valida o conteúdo, não a extensão."""
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (8, 8), (40, 80, 70)).save(buf, format="PNG")
        return SimpleUploadedFile(nome, buf.getvalue(), content_type="image/png")

    def _png_transparente(self, nome="logo.png"):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGBA", (12, 8), (20, 20, 20, 0)).save(buf, format="PNG")
        return SimpleUploadedFile(nome, buf.getvalue(), content_type="image/png")

    def test_envia_imagem_de_fundo_e_ela_entra_no_painel(self):
        resp = self.client.post(
            "/escritorio/identidade/",
            {"nome": self.grupo.empresa_registro.nome, "imagem_fundo": self._png()},
        )
        self.assertRedirects(resp, "/escritorio/identidade/")

        empresa = Empresa.objects.get(grupo=self.grupo)
        self.assertTrue(empresa.imagem_fundo)

        painel = self.client.get("/")
        self.assertContains(painel, "--fundo-escritorio")
        self.assertContains(painel, "/escritorio/identidade/fundo/")
        empresa.imagem_fundo.delete(save=True)

    def test_sem_imagem_o_painel_nao_declara_a_variavel(self):
        self.assertNotContains(self.client.get("/"), "--fundo-escritorio")

    def test_pdf_sem_logo_do_escritorio_usa_a_marca_do_app(self):
        identidade = _identidade_pdf(self.user)
        self.assertTrue(identidade["empresa_logo_data_uri"].startswith("data:image/svg+xml;base64,"))
        self.assertTrue(identidade["usando_logo_app"])
        pdf = render_pdf("pdf/base_pdf.html", {}, user=self.user)
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_remover_imagem_volta_para_o_padrao(self):
        self.client.post(
            "/escritorio/identidade/",
            {"nome": self.grupo.empresa_registro.nome, "imagem_fundo": self._png()},
        )
        self.client.post(
            "/escritorio/identidade/",
            {"nome": self.grupo.empresa_registro.nome, "limpar_fundo": "on"},
        )
        self.assertFalse(Empresa.objects.get(grupo=self.grupo).imagem_fundo)
        self.assertNotContains(self.client.get("/"), "--fundo-escritorio")

    def test_logo_transparente_e_preservada_no_menu_e_embutida_no_pdf(self):
        resposta = self.client.post(
            "/escritorio/identidade/",
            {"nome": self.grupo.empresa_registro.nome, "logo": self._png_transparente()},
        )
        self.assertRedirects(resposta, "/escritorio/identidade/")

        painel = self.client.get("/")
        self.assertContains(painel, 'class="app-brand-logo"')
        self.assertContains(painel, "/escritorio/identidade/logo/")

        identidade = _identidade_pdf(self.user)
        self.assertTrue(identidade["empresa_logo_data_uri"].startswith("data:image/png;base64,"))
        pdf = render_pdf("pdf/base_pdf.html", {}, user=self.user)
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))

        Empresa.objects.get(grupo=self.grupo).logo.delete(save=True)


class DadosDemoTests(TestCase):
    def test_comando_popula_a_empresa_certa_sem_duplicar(self):
        import io

        from django.core.management import call_command
        from precificacao.models import ConfiguracaoPrecificacao

        usuario, grupo = criar_empresa_e_usuario(username="admin_demo")
        saida = io.StringIO()
        call_command("popular_dados_demo", usuario=usuario.username, stdout=saida)
        primeira_contagem = Projeto.objects.filter(empresa=grupo).count()
        call_command("popular_dados_demo", usuario=usuario.username, stdout=saida)

        self.assertEqual(primeira_contagem, 4)
        self.assertEqual(Projeto.objects.filter(empresa=grupo).count(), 4)
        self.assertTrue(Projeto.objects.filter(empresa=grupo, tipo="urbanismo").exists())
        self.assertEqual(
            ConfiguracaoPrecificacao.objects.get(empresa=grupo).imposto_percent,
            Decimal("6.00"),
        )
