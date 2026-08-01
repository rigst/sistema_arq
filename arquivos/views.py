from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from projetos.models import Projeto

from .forms import ArquivoForm
from .models import Arquivo


def _meus(user):
    return queryset_da_empresa(
        Arquivo.objects.select_related("projeto", "fornecedor"), user
    )


@login_required
def lista(request):
    arquivos = _meus(request.user)

    fluxo = request.GET.get("fluxo", "")
    status = request.GET.get("status", "")
    projeto_id = request.GET.get("projeto", "")
    if fluxo:
        arquivos = arquivos.filter(fluxo=fluxo)
    if status:
        arquivos = arquivos.filter(status=status)
    if projeto_id.isdigit():
        arquivos = arquivos.filter(projeto_id=int(projeto_id))

    if request.method == "POST":
        form = ArquivoForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            arquivo = form.save(commit=False)
            arquivo.empresa = obter_grupo_empresa_ou_erro(request.user)
            arquivo.criado_por = request.user
            arquivo.save()
            messages.success(request, "Arquivo guardado.")
            return redirect("arquivos_lista")
        messages.error(request, "Confira os campos do arquivo.")
    else:
        form = ArquivoForm(user=request.user)

    return render(
        request,
        "arquivos/lista.html",
        {
            "arquivos": arquivos,
            "form": form,
            "fluxos": Arquivo.FLUXO_CHOICES,
            "status_choices": Arquivo.STATUS_CHOICES,
            "projetos": queryset_da_empresa(Projeto.objects.all(), request.user),
            "fluxo_ativo": fluxo,
            "status_ativo": status,
            "projeto_ativo": projeto_id,
        },
    )


@require_POST
@login_required
def mudar_status(request, pk):
    arquivo = get_object_or_404(_meus(request.user), pk=pk)
    novo = request.POST.get("status", "")
    if novo in dict(Arquivo.STATUS_CHOICES):
        arquivo.status = novo
        arquivo.save(update_fields=["status"])
        messages.success(request, f"{arquivo.titulo}: {arquivo.get_status_display().lower()}.")
    return redirect(request.POST.get("next") or "arquivos_lista")


@require_POST
@login_required
def remover(request, pk):
    arquivo = get_object_or_404(_meus(request.user), pk=pk)
    arquivo.arquivo.delete(save=False)
    arquivo.delete()
    messages.success(request, "Arquivo removido.")
    return redirect("arquivos_lista")
