import logging
import secrets
from hashlib import sha256

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.core.cache import cache
from django.shortcuts import redirect
from django.urls import reverse

from core.tenancy import nome_grupo_visitante
from core.request import ip_cliente

from .models import Usuario
from .visitantes import (
    excedeu_rate_limit_visitante,
    limpar_visitantes_expirados,
    registrar_tentativa_visitante,
)

logger = logging.getLogger(__name__)


class UsuarioLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def _client_ip(self):
        return ip_cliente(self.request)

    def _login_rate_key(self):
        identificador = self.request.POST.get("username", "").strip().casefold()
        origem = f"{self._client_ip()}|{identificador}".encode()
        return f"login:rate:{sha256(origem).hexdigest()}"

    def _registrar_falha(self, chave):
        if cache.add(chave, 1, timeout=900):
            return
        try:
            cache.incr(chave)
        except ValueError:
            cache.set(chave, 1, timeout=900)

    def post(self, request, *args, **kwargs):
        if "entrar_visitante" in request.POST:
            ip = self._client_ip()
            if excedeu_rate_limit_visitante(ip):
                logger.warning("Rate limit de visitante excedido", extra={"ip": ip})
                messages.error(
                    request,
                    "Muitas tentativas de acesso visitante em pouco tempo. "
                    "Aguarde alguns minutos e tente novamente.",
                )
                return redirect(reverse("login"))
            registrar_tentativa_visitante(ip)
            return self.criar_e_logar_visitante()
        chave = self._login_rate_key()
        if int(cache.get(chave, 0)) >= 8:
            logger.warning("Rate limit de login excedido", extra={"ip": self._client_ip()})
            messages.error(request, "Muitas tentativas. Aguarde 15 minutos e tente novamente.")
            form = self.get_form()
            return self.render_to_response(self.get_context_data(form=form), status=429)
        resposta = super().post(request, *args, **kwargs)
        if 300 <= resposta.status_code < 400:
            cache.delete(chave)
        else:
            self._registrar_falha(chave)
        return resposta

    def criar_e_logar_visitante(self):
        limpar_visitantes_expirados()
        token = secrets.token_hex(4)
        username = f"visitante_{token}"
        grupo = Group.objects.create(name=nome_grupo_visitante(username))
        usuario = Usuario.objects.create_user(
            username=username,
            password=secrets.token_urlsafe(24),
            perfil="visitante",
            nome_exibicao="Visitante",
        )
        usuario.groups.add(grupo)
        login(self.request, usuario)
        return redirect(reverse("dashboard"))


class UsuarioLogoutView(LogoutView):
    pass
