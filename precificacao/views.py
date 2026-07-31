from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import ConfiguracaoPrecificacaoForm, CustoFixoForm
from .models import CustoFixo
from .services import calcular_hora_tecnica, obter_configuracao, total_custos_fixos


@login_required
def painel_precificacao(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    config = obter_configuracao(grupo)

    if request.method == "POST" and "salvar_config" in request.POST:
        form_config = ConfiguracaoPrecificacaoForm(request.POST, instance=config)
        if form_config.is_valid():
            form_config.save()
            messages.success(request, "Parâmetros de precificação atualizados.")
            return redirect("precificacao")
    else:
        form_config = ConfiguracaoPrecificacaoForm(instance=config)

    custos = queryset_da_empresa(CustoFixo.objects.all(), request.user)
    return render(
        request,
        "precificacao/painel.html",
        {
            "custos": custos,
            "form_custo": CustoFixoForm(),
            "form_config": form_config,
            "hora_tecnica": calcular_hora_tecnica(grupo),
            "total_custos": total_custos_fixos(grupo),
            "config": config,
        },
    )


@require_POST
@login_required
def adicionar_custo(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    form = CustoFixoForm(request.POST)
    if form.is_valid():
        custo = form.save(commit=False)
        custo.empresa = grupo
        custo.criado_por = request.user
        custo.save()
        messages.success(request, "Custo fixo adicionado.")
    else:
        messages.error(request, "Verifique os dados do custo.")
    return redirect("precificacao")


@require_POST
@login_required
def remover_custo(request, pk):
    custo = get_object_or_404(
        queryset_da_empresa(CustoFixo.objects.all(), request.user), pk=pk
    )
    custo.delete()
    messages.success(request, "Custo removido.")
    return redirect("precificacao")
