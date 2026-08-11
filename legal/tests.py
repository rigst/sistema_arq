from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from legal.middleware import PREFIXOS_LIVRES, AceiteLegalMiddleware
from legal.models import AceiteLegal, DocumentoLegal
from legal.services import documento_vigente, documentos_pendentes
from usuarios.models import Usuario


def publicar(tipo, versao, quando=None):
    return DocumentoLegal.objects.create(
        tipo=tipo,
        versao=versao,
        titulo=f"{tipo} {versao}",
        conteudo="## Título\n\nUm parágrafo.\n\n- um item",
        vigente_desde=quando or timezone.now(),
    )


class DocumentosPublicosTests(TestCase):
    def test_paginas_publicas_abrem_sem_login(self):
        for url in ("/termos/", "/privacidade/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_pagina_404_quando_nao_ha_versao_vigente(self):
        DocumentoLegal.objects.all().update(vigente_desde=None)
        self.assertEqual(self.client.get("/termos/").status_code, 404)

    def test_versao_futura_nao_entra_em_vigor(self):
        vigente = documento_vigente(DocumentoLegal.TERMOS).versao
        futura = timezone.now() + timezone.timedelta(days=30)
        publicar(DocumentoLegal.TERMOS, "9.9", quando=futura)
        resposta = self.client.get("/termos/")
        self.assertEqual(resposta.context["documento"].versao, vigente)


class AceiteTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(username="ana", password="senha-de-teste-1")
        self.client.force_login(self.usuario)

    def test_usuario_sem_aceite_e_desviado_para_a_tela_de_aceite(self):
        resposta = self.client.get("/")
        self.assertRedirects(resposta, "/aceite/?next=%2F")

    def test_aceite_registra_data_ip_e_navegador(self):
        resposta = self.client.post(
            "/aceite/",
            {"aceito": "1", "next": "/"},
            REMOTE_ADDR="203.0.113.7",
            HTTP_USER_AGENT="Navegador de Teste/1.0",
        )
        self.assertRedirects(resposta, "/", fetch_redirect_response=False)

        aceites = AceiteLegal.objects.filter(usuario=self.usuario)
        self.assertEqual(aceites.count(), 2)
        for aceite in aceites:
            self.assertEqual(aceite.ip, "203.0.113.7")
            self.assertEqual(aceite.user_agent, "Navegador de Teste/1.0")
            self.assertIsNotNone(aceite.aceito_em)

    @override_settings(TRUST_X_FORWARDED_FOR=True)
    def test_ip_vem_do_x_forwarded_for_atras_de_proxy(self):
        self.client.post(
            "/aceite/",
            {"aceito": "1"},
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="198.51.100.4, 203.0.113.9",
        )
        self.assertEqual(AceiteLegal.objects.first().ip, "198.51.100.4")

    def test_sem_marcar_a_caixa_nada_e_registrado(self):
        resposta = self.client.post("/aceite/", {})
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(AceiteLegal.objects.exists())

    def test_depois_de_aceitar_navega_normalmente(self):
        self.client.post("/aceite/", {"aceito": "1"})
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_versao_nova_exige_aceite_de_novo(self):
        self.client.post("/aceite/", {"aceito": "1"})
        publicar(DocumentoLegal.TERMOS, "2.0")

        resposta = self.client.get("/")
        self.assertRedirects(resposta, "/aceite/?next=%2F")

        pendentes = documentos_pendentes(self.usuario)
        self.assertEqual([d.versao for d in pendentes], ["2.0"])

    def test_aceite_da_versao_antiga_continua_registrado(self):
        anterior = documento_vigente(DocumentoLegal.TERMOS).versao
        self.client.post("/aceite/", {"aceito": "1"})
        publicar(DocumentoLegal.TERMOS, "2.0")
        self.client.post("/aceite/", {"aceito": "1"})

        versoes = sorted(
            AceiteLegal.objects.filter(
                usuario=self.usuario, documento__tipo=DocumentoLegal.TERMOS
            ).values_list("documento__versao", flat=True)
        )
        self.assertEqual(versoes, sorted([anterior, "2.0"]))

    def test_termos_seguem_acessiveis_com_aceite_pendente(self):
        self.assertEqual(self.client.get("/termos/").status_code, 200)
        self.assertEqual(self.client.get("/privacidade/").status_code, 200)

    def test_aceite_e_idempotente(self):
        self.client.post("/aceite/", {"aceito": "1"})
        self.client.post("/aceite/", {"aceito": "1"})
        self.assertEqual(AceiteLegal.objects.filter(usuario=self.usuario).count(), 2)


class AllowlistExtraTests(TestCase):
    """LEGAL_ALLOWLIST_EXTRA acrescenta prefixos livres sem editar o módulo.

    Os testes instanciam o middleware direto em vez de usar o client: os
    prefixos são resolvidos no __init__, que roda uma única vez quando a
    cadeia de middlewares é montada. O override_settings do client não
    remonta essa cadeia, então passaria verde sem exercitar nada.
    """

    def setUp(self):
        self.usuario = Usuario.objects.create_user(username="bia", password="senha-de-teste-2")

    def montar(self):
        return AceiteLegalMiddleware(lambda request: HttpResponse("segue"))

    def pedir(self, middleware, caminho):
        pedido = RequestFactory().get(caminho)
        pedido.user = self.usuario
        return middleware(pedido)

    @override_settings(LEGAL_ALLOWLIST_EXTRA=("/webhook/",))
    def test_prefixo_extra_passa_com_aceite_pendente(self):
        self.assertEqual(self.pedir(self.montar(), "/webhook/pagamento/").content, b"segue")

    @override_settings(LEGAL_ALLOWLIST_EXTRA=("/webhook/",))
    def test_prefixo_extra_nao_libera_o_resto(self):
        self.assertEqual(self.pedir(self.montar(), "/contratos/").status_code, 302)

    def test_sem_a_setting_o_comportamento_nao_muda(self):
        middleware = self.montar()
        self.assertEqual(middleware.prefixos, PREFIXOS_LIVRES)
        self.assertEqual(self.pedir(middleware, "/contratos/").status_code, 302)


class VisitanteAceiteTests(TestCase):
    def test_visitante_cai_na_tela_de_aceite_depois_de_entrar(self):
        resposta = self.client.post("/login/", {"entrar_visitante": "1"}, follow=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.request["PATH_INFO"], "/aceite/")
        self.assertTemplateUsed(resposta, "legal/aceite.html")

    def test_aceite_do_visitante_fica_registrado_com_ip(self):
        self.client.post("/login/", {"entrar_visitante": "1"})
        self.client.post("/aceite/", {"aceito": "1"}, REMOTE_ADDR="192.0.2.10")

        visitante = Usuario.objects.get(perfil="visitante")
        self.assertEqual(visitante.aceites_legais.count(), 2)
        self.assertEqual(visitante.aceites_legais.first().ip, "192.0.2.10")
