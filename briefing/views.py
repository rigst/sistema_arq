from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .forms import AmbienteForm, BriefingForm
from .models import AmbientePrograma, Briefing


def _get_briefing(request, projeto_pk):
    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.all(), request.user), pk=projeto_pk
    )
    briefing, _ = Briefing.objects.get_or_create(
        projeto=projeto, defaults={"empresa": projeto.empresa, "criado_por": request.user}
    )
    return projeto, briefing


@login_required
def editar_briefing(request, projeto_pk):
    projeto, briefing = _get_briefing(request, projeto_pk)
    if request.method == "POST":
        form = BriefingForm(request.POST, instance=briefing)
        if form.is_valid():
            form.save()
            messages.success(request, "Briefing salvo.")
            return redirect("briefing_projeto", projeto_pk=projeto.pk)
    else:
        form = BriefingForm(instance=briefing)
    return render(
        request,
        "briefing/form.html",
        {
            "projeto": projeto,
            "briefing": briefing,
            "form": form,
            "ambientes": briefing.ambientes.all(),
            "form_ambiente": AmbienteForm(),
        },
    )


@require_POST
@login_required
def adicionar_ambiente(request, projeto_pk):
    projeto, briefing = _get_briefing(request, projeto_pk)
    form = AmbienteForm(request.POST)
    if form.is_valid():
        ambiente = form.save(commit=False)
        ambiente.briefing = briefing
        ambiente.empresa = projeto.empresa
        ambiente.save()
        messages.success(request, "Ambiente adicionado ao programa de necessidades.")
    return redirect("briefing_projeto", projeto_pk=projeto.pk)


@require_POST
@login_required
def remover_ambiente(request, pk):
    ambiente = get_object_or_404(
        queryset_da_empresa(AmbientePrograma.objects.all(), request.user), pk=pk
    )
    projeto_pk = ambiente.briefing.projeto_id
    ambiente.delete()
    return redirect("briefing_projeto", projeto_pk=projeto_pk)
