from unittest.mock import MagicMock, patch

from django.db import OperationalError
from django.test import Client, TestCase, override_settings

from core.factories import criar_empresa_e_usuario
from core.healthz import _broker

URL = "/healthz/"


class HealthzTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")

    def test_200_com_banco_cache_e_broker_ok(self):
        resposta = self.client.get(URL)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"status": "ok"})
        self.assertIn("no-cache", resposta["Cache-Control"])

    def test_503_quando_o_banco_falha(self):
        with (
            patch("core.healthz.connection.cursor", side_effect=OperationalError("fora")),
            self.assertLogs("core.healthz", level="ERROR") as logs,
        ):
            resposta = self.client.get(URL)
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(resposta.json(), {"status": "indisponivel"})
        self.assertIn("banco", logs.output[0])

    def test_503_quando_o_cache_falha(self):
        with (
            patch("core.healthz.cache.set", side_effect=ConnectionError("redis fora")),
            self.assertLogs("core.healthz", level="ERROR") as logs,
        ):
            resposta = self.client.get(URL)
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("cache", logs.output[0])

    def test_503_quando_o_cache_nao_devolve_o_valor(self):
        with (
            patch("core.healthz.cache.get", return_value=None),
            self.assertLogs("core.healthz", level="ERROR"),
        ):
            resposta = self.client.get(URL)
        self.assertEqual(resposta.status_code, 503)

    @override_settings(CELERY_BROKER_URL="redis://localhost:1/0", CELERY_TASK_ALWAYS_EAGER=False)
    def test_503_quando_o_broker_falha(self):
        with (
            patch("config.celery.app.connection_for_write", side_effect=OSError("broker fora")),
            self.assertLogs("core.healthz", level="ERROR") as logs,
        ):
            resposta = self.client.get(URL)
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("broker", logs.output[0])

    @override_settings(CELERY_BROKER_URL="redis://localhost:1/0", CELERY_TASK_ALWAYS_EAGER=False)
    def test_broker_ok_abre_conexao_com_timeout_curto(self):
        conexao = MagicMock()
        with patch("config.celery.app.connection_for_write") as conectar:
            conectar.return_value.__enter__.return_value = conexao
            _broker()
        conexao.ensure_connection.assert_called_once_with(max_retries=1, timeout=3)

    @override_settings(CELERY_BROKER_URL="", CELERY_TASK_ALWAYS_EAGER=True)
    def test_sem_broker_nao_sonda_celery(self):
        with patch("config.celery.app.connection_for_write") as conectar:
            _broker()
        conectar.assert_not_called()

    @override_settings(HEALTHZ_TOKEN="token-de-teste")
    def test_404_sem_token(self):
        self.assertEqual(self.client.get(URL).status_code, 404)

    @override_settings(HEALTHZ_TOKEN="token-de-teste")
    def test_404_com_token_errado(self):
        self.assertEqual(self.client.get(URL, HTTP_X_HEALTHZ_TOKEN="outro").status_code, 404)

    @override_settings(HEALTHZ_TOKEN="token-de-teste")
    def test_200_com_token_certo(self):
        resposta = self.client.get(URL, HTTP_X_HEALTHZ_TOKEN="token-de-teste")
        self.assertEqual(resposta.status_code, 200)

    def test_post_nao_e_aceito(self):
        self.assertEqual(self.client.post(URL).status_code, 405)

    def test_usuario_com_aceite_pendente_nao_e_redirecionado(self):
        # O smoke-test só aceita 200: um 302 do AceiteLegalMiddleware
        # derrubaria o deploy. Sem documento aceito, qualquer rota comum
        # redirecionaria para /aceite/.
        usuario, _grupo = criar_empresa_e_usuario()
        self.client.force_login(usuario)
        with patch("legal.middleware.documentos_pendentes", return_value=True):
            resposta = self.client.get(URL)
        self.assertEqual(resposta.status_code, 200)
