from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from core.factories import criar_empresa_e_usuario

from .models import ObrigacaoTecnica


class ObrigacaoModelTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()

    def test_vencida(self):
        o = ObrigacaoTecnica.objects.create(
            empresa=self.grupo, tipo="art", status="registrada",
            vencimento=timezone.localdate() - timedelta(days=1),
        )
        self.assertTrue(o.vencida)
        self.assertFalse(o.vencendo)

    def test_vencendo_dentro_da_janela(self):
        o = ObrigacaoTecnica.objects.create(
            empresa=self.grupo, tipo="rrt", status="registrada",
            vencimento=timezone.localdate() + timedelta(days=10),
        )
        self.assertTrue(o.vencendo)
        self.assertFalse(o.vencida)

    def test_baixada_nao_alerta(self):
        o = ObrigacaoTecnica.objects.create(
            empresa=self.grupo, tipo="art", status="baixada",
            vencimento=timezone.localdate() - timedelta(days=5),
        )
        self.assertFalse(o.vencida)
        self.assertFalse(o.vencendo)


class RegulatorioViewTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.client = Client(SERVER_NAME="localhost")
        self.client.force_login(self.user)

    def test_criar_e_baixar(self):
        resp = self.client.post(
            "/regulatorio/nova/",
            {"tipo": "art", "numero": "BR123", "status": "pendente", "valor": "0"},
        )
        self.assertEqual(resp.status_code, 302)
        o = ObrigacaoTecnica.objects.get(numero="BR123")
        self.client.post(f"/regulatorio/{o.pk}/baixar/")
        o.refresh_from_db()
        self.assertEqual(o.status, "baixada")

    def test_lista_200(self):
        self.assertEqual(self.client.get("/regulatorio/").status_code, 200)
