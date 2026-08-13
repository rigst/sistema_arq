import secrets
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.factories import SENHA_ERRADA, SENHA_TESTE
from core.models import Empresa
from core.tenancy import nome_grupo_visitante, obter_grupo_empresa_padrao
from usuarios.models import Usuario
from usuarios.tasks import limpar_visitantes_expirados_task
from usuarios.visitantes import (
    excedeu_rate_limit_visitante,
    limpar_dados_visitante,
    limpar_visitantes_expirados,
    registrar_tentativa_visitante,
)


class LoginSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = Usuario.objects.create_user(username="login-seguro", password=SENHA_TESTE)

    def test_bloqueia_depois_de_oito_falhas(self):
        for _ in range(8):
            self.client.post(
                "/login/",
                {"username": self.user.username, "password": SENHA_ERRADA},
                REMOTE_ADDR="203.0.113.10",
            )
        resposta = self.client.post(
            "/login/",
            {"username": self.user.username, "password": SENHA_ERRADA},
            REMOTE_ADDR="203.0.113.10",
        )
        self.assertEqual(resposta.status_code, 429)
        self.assertContains(resposta, "Muitas tentativas", status_code=429)


class AdminSecurityTests(TestCase):
    def test_superusuario_acessa_criacao_com_campos_adicionais(self):
        superusuario = Usuario.objects.create_superuser(
            username="root-admin", password=SENHA_TESTE, email="root@example.com"
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
            username="admin-tenant", password=SENHA_TESTE, perfil="admin", is_staff=True
        )
        staff.groups.add(grupo)
        self.client.force_login(staff)
        resposta = self.client.get("/admin/")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/admin/login/", resposta.url)


class VisitanteRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_conta_tentativas_ate_estourar_o_limite(self):
        ip = "203.0.113.20"
        self.assertFalse(excedeu_rate_limit_visitante(ip))
        for _ in range(20):
            registrar_tentativa_visitante(ip)
        self.assertTrue(excedeu_rate_limit_visitante(ip))

    def test_chave_que_expira_entre_add_e_incr_reinicia_a_janela(self):
        # Corrida real: o add não cria porque a chave existe, mas ela expira
        # antes do incr — que então levanta ValueError por chave inexistente.
        # O tratamento recomeça a contagem em vez de derrubar o login.
        ip = "203.0.113.21"
        with mock.patch.object(cache, "add", return_value=False):
            registrar_tentativa_visitante(ip)
        self.assertEqual(cache.get(f"visitante:rate:{ip}"), 1)

    def test_ip_vazio_tem_chave_propria(self):
        registrar_tentativa_visitante("")
        self.assertIsNotNone(cache.get("visitante:rate:desconhecido"))


class VisitanteLimpezaTests(TestCase):
    def _criar_visitante(self, username="visitante_abc"):
        grupo = Group.objects.create(name=nome_grupo_visitante(username))
        usuario = Usuario.objects.create_user(
            username=username,
            password=secrets.token_urlsafe(24),
            perfil="visitante",
            nome_exibicao="Visitante",
        )
        usuario.groups.add(grupo)
        return usuario, grupo

    def test_limpar_dados_visitante_remove_usuario_grupo_e_empresa(self):
        usuario, grupo = self._criar_visitante()
        Empresa.objects.get_or_create(grupo=grupo, defaults={"nome": "Visitante"})

        limpar_dados_visitante(usuario)

        self.assertFalse(Usuario.objects.filter(pk=usuario.pk).exists())
        self.assertFalse(Group.objects.filter(pk=grupo.pk).exists())
        self.assertFalse(Empresa.objects.filter(grupo_id=grupo.pk).exists())

    def test_limpar_dados_visitante_ignora_usuario_comum(self):
        comum = Usuario.objects.create_user(username="equipe-1", password=SENHA_TESTE)
        limpar_dados_visitante(comum)
        self.assertTrue(Usuario.objects.filter(pk=comum.pk).exists())

    def test_limpar_dados_visitante_ignora_none(self):
        limpar_dados_visitante(None)

    def test_expurgo_remove_apenas_quem_passou_do_ttl(self):
        antigo, _ = self._criar_visitante("visitante_velho")
        recente, _ = self._criar_visitante("visitante_novo")
        Usuario.objects.filter(pk=antigo.pk).update(criado_em=timezone.now() - timedelta(hours=48))

        self.assertEqual(limpar_visitantes_expirados(), 1)
        self.assertFalse(Usuario.objects.filter(pk=antigo.pk).exists())
        self.assertTrue(Usuario.objects.filter(pk=recente.pk).exists())

    def test_task_do_celery_delega_para_o_expurgo(self):
        self.assertEqual(limpar_visitantes_expirados_task(), 0)

    def test_comando_de_gestao_reporta_o_total(self):
        saida = StringIO()
        call_command("limpar_visitantes_expirados", stdout=saida)
        self.assertIn("Limpeza concluída", saida.getvalue())
