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
        ("Primeiros passos", "Implantação guiada em 5 etapas.", "onboarding", True),
        ("CRM e clientes", "Contatos, funil e histórico de cada cliente.", "crm_lista", True),
        ("Precificação", "Hora técnica a partir dos custos fixos.", "precificacao", True),
        ("Propostas", "Gerador de proposta que vira projeto ao aprovar.", "proposta_nova", True),
        ("Projetos e etapas", "Painel com etapa, pendências e margem.", "projetos_painel", True),
        ("Tarefas e horas", "Delegação com dono, prazo e timer.", "tarefas_lista", True),
        ("Financeiro", "Entradas, saídas, saldos e margem por projeto.", "financeiro_painel", True),
        ("Contratos", "Parcelas no financeiro, aditivos e documentos.", "contratos_lista", True),
        ("Agenda", "Reuniões, visitas e prazos vinculados.", "agenda", True),
        ("Obras", "Visitas técnicas, cronograma real × previsto e medições.", "obras_lista", True),
        ("Regulatório", "ART, RRT e vínculo CAU com alerta de vencimento.", "regulatorio_lista", True),
        ("Notificações", "Prazos, projetos parados e desvios — automáticos.", "notificacoes_lista", True),
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
