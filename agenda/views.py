from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from fases.models import Fase
from fases.services import garantir_tarefas_da_fase
from tarefas.models import Tarefa

from . import calendario
from .forms import CompromissoForm
from .models import Compromisso


def _mes_pedido(request, hoje):
    """Mês da URL, com queda para o mês corrente quando vier bobagem."""
    try:
        ano = int(request.GET.get("ano", hoje.year))
        mes = int(request.GET.get("mes", hoje.month))
        date(ano, mes, 1)
    except (TypeError, ValueError):
        return hoje.year, hoje.month
    return ano, mes


@login_required
def agenda(request):
    hoje = timezone.localdate()
    ano, mes = _mes_pedido(request, hoje)
    projeto = projeto_do_pedido(request)

    if request.method == "POST":
        form = CompromissoForm(request.POST, user=request.user)
        if form.is_valid():
            compromisso = form.save(commit=False)
            compromisso.empresa = obter_grupo_empresa_ou_erro(request.user)
            compromisso.criado_por = request.user
            if projeto is not None and compromisso.projeto_id is None:
                compromisso.projeto = projeto
            compromisso.save()
            quando = timezone.localtime(compromisso.inicio)
            messages.success(request, f"{compromisso.get_tipo_display()} “{compromisso.titulo}” agendada para {quando:%d/%m às %H:%M}.")
            return redirect(f"{reverse('agenda')}?ano={ano}&mes={mes}")
        messages.error(request, "Confira os campos do compromisso.")
    else:
        form = CompromissoForm(user=request.user)

    base = queryset_da_empresa(
        Compromisso.objects.select_related("cliente", "projeto"), request.user
    )
    if projeto is not None:
        base = base.filter(projeto=projeto)

    # A grade abrange dias vizinhos, então a busca vai um pouco além do mês.
    semanas = calendario.montar_mes(ano, mes, [], hoje)
    primeiro, ultimo = semanas[0][0].data, semanas[-1][-1].data
    do_periodo = base.filter(inicio__date__gte=primeiro, inicio__date__lte=ultimo)

    fases_tecnicas = queryset_da_empresa(
        Fase.objects.select_related("projeto").filter(tarefas_semeadas=False)
        .exclude(status=Fase.NAO_INICIADA).exclude(
            chave__in={"briefing", "proposta", "contrato"}
        ),
        request.user,
    )
    if projeto is not None:
        fases_tecnicas = fases_tecnicas.filter(projeto=projeto)
    for fase in fases_tecnicas:
        garantir_tarefas_da_fase(fase, request.user)

    tarefas = queryset_da_empresa(
        Tarefa.objects.select_related("projeto", "fase").filter(
            fase__isnull=False, prazo__gte=primeiro, prazo__lte=ultimo
        ).exclude(fase__status=Fase.NAO_INICIADA),
        request.user,
    )
    if projeto is not None:
        tarefas = tarefas.filter(projeto=projeto)
    tarefas = tarefas.order_by("prazo", "fase__ordem", "ordem", "id")
    semanas = calendario.montar_mes(
        ano, mes, [*do_periodo, *tarefas], hoje
    )

    anterior, seguinte = calendario.vizinhos(ano, mes)
    return render(
        request,
        "agenda/agenda.html",
        {
            "form": form,
            "projeto": projeto,
            "semanas": semanas,
            "dias_semana": calendario.DIAS_SEMANA,
            "titulo_mes": calendario.nome_do_mes(ano, mes),
            "ano": ano,
            "mes": mes,
            "anterior": {"ano": anterior[0], "mes": anterior[1]},
            "seguinte": {"ano": seguinte[0], "mes": seguinte[1]},
            "eh_mes_corrente": (ano, mes) == (hoje.year, hoje.month),
            "do_mes": [
                (c, CompromissoForm(instance=c, user=request.user))
                for c in do_periodo
                if calendario.dia_local(c).month == mes
            ],
            "tarefas_do_mes": [t for t in tarefas if t.prazo.month == mes],
            "proximos": base.filter(inicio__gte=timezone.now())[:8],
        },
    )


@require_POST
@login_required
def editar_compromisso(request, pk):
    """Edição pelo modal da própria linha: sair da agenda para mudar um horário
    e voltar custa mais do que a mudança."""
    compromisso = get_object_or_404(
        queryset_da_empresa(Compromisso.objects.all(), request.user), pk=pk
    )
    form = CompromissoForm(request.POST, instance=compromisso, user=request.user)
    if form.is_valid():
        form.save()
        quando = timezone.localtime(compromisso.inicio)
        messages.success(
            request,
            f"Compromisso “{compromisso.titulo}” atualizado para "
            f"{quando:%d/%m às %H:%M}.",
        )
    else:
        messages.error(request, "Confira os campos do compromisso.")
    # Volta para o mês em que o compromisso aparece na grade, que é o local.
    quando = timezone.localtime(compromisso.inicio)
    return redirect(f"{reverse('agenda')}?ano={quando.year}&mes={quando.month}")


@require_POST
@login_required
def remover_compromisso(request, pk):
    compromisso = get_object_or_404(
        queryset_da_empresa(Compromisso.objects.all(), request.user), pk=pk
    )
    titulo = compromisso.titulo
    compromisso.delete()
    messages.success(request, f"Compromisso “{titulo}” removido da agenda.")
    return redirect("agenda")
