import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.tenancy import definir_empresa_ativa, obter_empresa_ativa_usuario


def healthz(request):
    healthz_token = getattr(settings, "HEALTHZ_TOKEN", "")
    if healthz_token:
        token_recebido = request.headers.get("X-Healthz-Token", "").strip()
        if not token_recebido or not secrets.compare_digest(token_recebido, healthz_token):
            return HttpResponseNotFound()
    return JsonResponse({"status": "ok"})


@login_required
def dashboard(request):
    """Painel inicial. Na Fase 0 é só o esqueleto que confirma o acesso e a
    empresa ativa; os módulos (projetos, financeiro, etc.) entram nas próximas fases."""
    empresa = obter_empresa_ativa_usuario(request.user)
    modulos = [
        ("CRM e clientes", "Contatos, funil e histórico de cada cliente.", "Fase 1"),
        ("Precificação", "Hora técnica a partir dos custos fixos.", "Fase 1"),
        ("Propostas", "Gerador de proposta com identidade do escritório.", "Fase 1"),
        ("Projetos e etapas", "Templates, painel e acompanhamento.", "Fase 1"),
        ("Tarefas e horas", "Delegação com dono, prazo e timer.", "Fase 1"),
        ("Financeiro", "Entradas, saídas e margem por projeto.", "Fase 1"),
        ("Contratos e briefing", "Documentos e escopo por projeto.", "Fase 2"),
        ("Agenda", "Reuniões e visitas vinculadas.", "Fase 2"),
        ("Obras", "Visitas, avanço e medições.", "Fase 4"),
    ]
    return render(
        request,
        "core/dashboard.html",
        {"empresa": empresa, "modulos": modulos},
    )


@require_POST
@login_required
def alternar_empresa(request):
    empresa = definir_empresa_ativa(request, request.user, request.POST.get("empresa_id"))
    if empresa is None:
        messages.error(request, "Não foi possível alternar a empresa.")
    else:
        messages.success(request, f"Empresa ativa: {empresa.nome}.")

    destino = request.POST.get("next", "")
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(destino)
    return redirect(reverse("dashboard"))
