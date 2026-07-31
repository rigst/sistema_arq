from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import CompromissoForm
from .models import Compromisso


@login_required
def agenda(request):
    if request.method == "POST":
        form = CompromissoForm(request.POST, user=request.user)
        if form.is_valid():
            compromisso = form.save(commit=False)
            compromisso.empresa = obter_grupo_empresa_ou_erro(request.user)
            compromisso.criado_por = request.user
            compromisso.save()
            messages.success(request, "Compromisso agendado.")
            return redirect("agenda")
    else:
        form = CompromissoForm(user=request.user)

    base = queryset_da_empresa(
        Compromisso.objects.select_related("cliente", "projeto"), request.user
    )
    agora = timezone.now()
    return render(
        request,
        "agenda/agenda.html",
        {
            "form": form,
            "proximos": base.filter(inicio__gte=agora),
            "passados": base.filter(inicio__lt=agora).order_by("-inicio")[:20],
        },
    )


@require_POST
@login_required
def remover_compromisso(request, pk):
    compromisso = get_object_or_404(
        queryset_da_empresa(Compromisso.objects.all(), request.user), pk=pk
    )
    compromisso.delete()
    messages.success(request, "Compromisso removido.")
    return redirect("agenda")
