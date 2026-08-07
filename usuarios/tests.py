from django.core.cache import cache
from django.test import TestCase

from core.tenancy import obter_grupo_empresa_padrao
from usuarios.models import Usuario


class LoginSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = Usuario.objects.create_user(username="login-seguro", password="senha-forte-123")

    def test_bloqueia_depois_de_oito_falhas(self):
        for _ in range(8):
            self.client.post(
                "/login/",
                {"username": self.user.username, "password": "errada"},
                REMOTE_ADDR="203.0.113.10",
            )
        resposta = self.client.post(
            "/login/",
            {"username": self.user.username, "password": "errada"},
            REMOTE_ADDR="203.0.113.10",
        )
        self.assertEqual(resposta.status_code, 429)
        self.assertContains(resposta, "Muitas tentativas", status_code=429)


class AdminSecurityTests(TestCase):
    def test_superusuario_acessa_criacao_com_campos_adicionais(self):
        superusuario = Usuario.objects.create_superuser(
            username="root-admin", password="senha-forte-123", email="root@example.com"
        )
        self.client.force_login(superusuario)
        resposta = self.client.get("/admin/usuarios/usuario/add/")
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "nome_exibicao")
        self.assertContains(resposta, "perfil")
        self.assertContains(resposta, "groups")

    def test_staff_de_empresa_nao_acessa_admin_global(self):
        grupo = obter_grupo_empresa_padrao()
        staff = Usuario.objects.create_user(
            username="admin-tenant", password="senha-forte-123", perfil="admin", is_staff=True
        )
        staff.groups.add(grupo)
        self.client.force_login(staff)
        resposta = self.client.get("/admin/")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/admin/login/", resposta.url)
