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
    """Painel inicial — cockpit: indicadores do escritório, próximo passo da
    implantação e atalhos agrupados por área."""
    from decimal import Decimal

    from django.db.models import Sum

    from core.tenancy import queryset_da_empresa
    from financeiro.models import Lancamento
    from obras.models import Obra
    from onboarding.checklist import montar_checklist
    from projetos.models import Projeto
    from regulatorio.models import ObrigacaoTecnica
    from tarefas.models import Tarefa

    empresa = obter_empresa_ativa_usuario(request.user)
    u = request.user

    projetos_ativos = queryset_da_empresa(Projeto.objects.all(), u).filter(status="ativo").count()
    obras = list(queryset_da_empresa(Obra.objects.prefetch_related("etapas"), u))
    obras_desvio = sum(1 for o in obras if o.em_desvio)
    tarefas_abertas = queryset_da_empresa(Tarefa.objects.all(), u).exclude(status="concluida").count()
    a_receber = queryset_da_empresa(Lancamento.objects.all(), u).filter(
        tipo="entrada", status="previsto"
    ).aggregate(s=Sum("valor"))["s"] or Decimal("0")
    obrigacoes = queryset_da_empresa(ObrigacaoTecnica.objects.all(), u).exclude(status="baixada")
    obrig_alerta = sum(1 for o in obrigacoes if o.vencida or o.vencendo or o.pendente_registro)

    kpis = [
        {"label": "Projetos ativos", "valor": projetos_ativos, "rodape": "em andamento", "url": "projetos_painel", "cor": "blue"},
        {"label": "Obras em desvio", "valor": obras_desvio, "rodape": "atrás do previsto", "url": "obras_lista", "cor": "alert" if obras_desvio else "green"},
        {"label": "A receber (previsto)", "valor": f"R$ {a_receber}", "rodape": "lançamentos previstos", "url": "financeiro_painel", "cor": "green"},
        {"label": "Tarefas abertas", "valor": tarefas_abertas, "rodape": "a fazer", "url": "tarefas_lista", "cor": "violet"},
    ]

    onboarding = montar_checklist(u)

    # O painel não repete o menu. A barra lateral já lista os módulos; repetir
    # tudo em cartão não informava nada e ainda dava a impressão de que existem
    # duas formas diferentes de chegar no mesmo lugar. No lugar disso, a única
    # pergunta que o painel precisa responder: em que pé está cada projeto e
    # qual é o próximo passo dele.
    from jornada.roteiro import montar_roteiro, percentual, proxima_etapa

    frentes = []
    for projeto in (
        queryset_da_empresa(Projeto.objects.select_related("cliente"), u)
        .filter(status="ativo")
        .order_by("-ultima_atualizacao")[:8]
    ):
        etapas = montar_roteiro(projeto)
        frentes.append(
            {
                "projeto": projeto,
                "proxima": proxima_etapa(etapas),
                "percentual": percentual(etapas),
                "feitas": sum(1 for e in etapas if e.concluida),
                "total": len(etapas),
            }
        )

    return render(
        request,
        "core/dashboard.html",
        {
            "empresa": empresa,
            "kpis": kpis,
            "onboarding": onboarding,
            "frentes": frentes,
            "obrig_alerta": obrig_alerta,
        },
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
