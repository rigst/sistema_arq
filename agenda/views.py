from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

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
            messages.success(request, f"{compromisso.get_tipo_display()} “{compromisso.titulo}” agendada para {compromisso.inicio:%d/%m às %H:%M}.")
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
    semanas = calendario.montar_mes(ano, mes, do_periodo, hoje)

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
                c for c in do_periodo if c.inicio.date().month == mes
            ],
            "proximos": base.filter(inicio__gte=timezone.now())[:8],
        },
    )


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
