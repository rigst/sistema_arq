from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings

from core.factories import criar_empresa_e_usuario
from core.security_headers import PermissionsPolicyMiddleware

POLITICA_PADRAO = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"


class PermissionsPolicyRotasTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")

    def test_rota_publica_manda_o_cabecalho(self):
        resposta = self.client.get("/login/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Permissions-Policy"], POLITICA_PADRAO)

    def test_healthz_manda_o_cabecalho(self):
        resposta = self.client.get("/healthz/")
        self.assertEqual(resposta["Permissions-Policy"], POLITICA_PADRAO)

    def test_admin_logado_manda_o_cabecalho(self):
        usuario, _ = criar_empresa_e_usuario()
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.save()
        self.client.force_login(usuario)
        resposta = self.client.get("/admin/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Permissions-Policy"], POLITICA_PADRAO)


class PermissionsPolicyMiddlewareTests(SimpleTestCase):
    def _resposta(self, view_response):
        middleware = PermissionsPolicyMiddleware(lambda request: view_response)
        return middleware(RequestFactory().get("/"))

    def test_respeita_valor_definido_pela_view(self):
        resposta_view = HttpResponse()
        resposta_view["Permissions-Policy"] = "camera=(self)"
        self.assertEqual(self._resposta(resposta_view)["Permissions-Policy"], "camera=(self)")

    @override_settings(PERMISSIONS_POLICY="")
    def test_valor_vazio_desliga_o_cabecalho(self):
        self.assertNotIn("Permissions-Policy", self._resposta(HttpResponse()))
