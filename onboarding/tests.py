from django.test import Client, TestCase

from core.factories import criar_empresa_e_usuario
from crm.models import Cliente

from .checklist import montar_checklist
from legal.testing import aceitar_documentos


class OnboardingChecklistTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()

    def test_checklist_vazio(self):
        c = montar_checklist(self.user)
        self.assertEqual(c["concluidas"], 0)
        self.assertFalse(c["completo"])
        self.assertTrue(c["etapas"][0]["atual"])

    def test_primeira_etapa_conclui_com_cliente(self):
        Cliente.objects.create(empresa=self.grupo, nome="Primeiro")
        c = montar_checklist(self.user)
        self.assertEqual(c["concluidas"], 1)
        self.assertTrue(c["etapas"][0]["concluida"])
        # A próxima etapa a fazer passa a ser a segunda.
        self.assertTrue(c["etapas"][1]["atual"])


class OnboardingViewTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.client = Client(SERVER_NAME="localhost")
        self.client.force_login(self.user)
        aceitar_documentos(self.user)

    def test_pagina_200(self):
        self.assertEqual(self.client.get("/onboarding/").status_code, 200)
