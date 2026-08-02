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
    from projetos.models import Projeto
    from regulatorio.models import ObrigacaoTecnica

    empresa = obter_empresa_ativa_usuario(request.user)
    u = request.user

    projetos_ativos = queryset_da_empresa(Projeto.objects.all(), u).filter(status="ativo").count()
    a_receber = queryset_da_empresa(Lancamento.objects.all(), u).filter(
        tipo="entrada", status="previsto"
    ).aggregate(s=Sum("valor"))["s"] or Decimal("0")
    obrigacoes = queryset_da_empresa(ObrigacaoTecnica.objects.all(), u).exclude(status="baixada")
    obrig_alerta = sum(1 for o in obrigacoes if o.vencida or o.vencendo or o.pendente_registro)

    # Fases é o que o escritório realmente acompanha: quantas estão paradas
    # com o cliente é a informação que muda o dia, mais do que um total de
    # projetos que quase nunca varia.
    from fases.models import Fase

    fases = queryset_da_empresa(Fase.objects.select_related("projeto"), u)
    com_cliente = fases.filter(status=Fase.AGUARDANDO).count()
    em_elaboracao = fases.filter(status=Fase.EM_ELABORACAO).count()
    com_ajustes = fases.filter(status=Fase.AJUSTES).count()

    # A cor é a identidade do indicador, não o alarme: trocá-la conforme o
    # valor fazia os cinco ficarem verdes num dia calmo, e aí a cor não
    # distinguia mais nada. Quem responde pelo alarme é `aceso` — o número só
    # ganha cor quando há algo ali para olhar.
    kpis = [
        {"label": "Projetos ativos", "valor": projetos_ativos, "rodape": "em andamento", "url": "projetos_painel", "cor": "blue", "aceso": bool(projetos_ativos)},
        {"label": "Fases em elaboração", "valor": em_elaboracao, "rodape": "sendo desenhadas agora", "url": "projetos_painel", "cor": "green", "aceso": bool(em_elaboracao)},
        {"label": "Aguardando cliente", "valor": com_cliente, "rodape": "enviadas, sem resposta", "url": "projetos_painel", "cor": "amber", "aceso": bool(com_cliente)},
        {"label": "Ajustes pedidos", "valor": com_ajustes, "rodape": "cliente devolveu", "url": "projetos_painel", "cor": "alert", "aceso": bool(com_ajustes)},
        {"label": "A receber (previsto)", "valor": f"R$ {a_receber}", "rodape": "lançamentos previstos", "url": "financeiro_painel", "cor": "violet", "aceso": a_receber > 0},
    ]

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
        proxima = proxima_etapa(etapas)
        frentes.append(
            {
                "projeto": projeto,
                "proxima": proxima,
                "percentual": percentual(etapas),
                "feitas": sum(1 for e in etapas if e.concluida),
                "total": len(etapas),
                # O estado da fase é o que diz se a bola está com o escritório
                # ou com o cliente — e é isso que decide o que fazer hoje.
                "situacao": proxima.resumo if proxima else "roteiro completo",
                "status": proxima.status if proxima else "aprovada",
                "aguardando": bool(proxima and proxima.status == "aguardando_cliente"),
            }
        )

    return render(
        request,
        "core/dashboard.html",
        {
            "empresa": empresa,
            "kpis": kpis,
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


@login_required
def identidade(request):
    """Marca e imagem de fundo do escritório."""
    from core.forms_empresa import IdentidadeEmpresaForm

    empresa = obter_empresa_ativa_usuario(request.user)
    if empresa is None:
        raise PermissionDenied("Usuário sem empresa vinculada.")

    if request.method == "POST":
        form = IdentidadeEmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, "Identidade do escritório atualizada.")
            return redirect("identidade")
    else:
        form = IdentidadeEmpresaForm(instance=empresa)

    return render(request, "core/identidade.html", {"form": form, "empresa": empresa})
