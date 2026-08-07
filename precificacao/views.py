from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import ConfiguracaoPrecificacaoForm, CustoFixoForm, FatorPrecificacaoForm
from .models import CustoFixo, FatorPrecificacao
from .services import (
    custo_hora,
    hora_tecnica_base,
    obter_configuracao,
    precificar_etapa,
    total_custos_fixos,
)


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
    fatores = queryset_da_empresa(FatorPrecificacao.objects.all(), request.user)
    custo = custo_hora(grupo)
    hora_base = hora_tecnica_base(grupo)
    previa = precificar_etapa(grupo, 1, hora_tecnica=hora_base)
    return render(
        request,
        "precificacao/painel.html",
        {
            "custos": custos,
            "fatores": fatores,
            "form_custo": CustoFixoForm(),
            "form_config": form_config,
            "form_fator": FatorPrecificacaoForm(),
            "custo_hora": custo,
            "hora_base": hora_base,
            "imposto_hora": previa["imposto"],
            "lucro_hora": previa["lucro_previsto"],
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
    custo = get_object_or_404(queryset_da_empresa(CustoFixo.objects.all(), request.user), pk=pk)
    custo.delete()
    messages.success(request, "Custo removido.")
    return redirect("precificacao")


@require_POST
@login_required
def adicionar_fator(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    form = FatorPrecificacaoForm(request.POST)
    if form.is_valid():
        fator = form.save(commit=False)
        fator.empresa = grupo
        fator.save()
        messages.success(request, "Fator de precificação adicionado.")
    else:
        messages.error(request, "Informe nome e percentual do fator.")
    return redirect("precificacao")


@require_POST
@login_required
def remover_fator(request, pk):
    fator = get_object_or_404(
        queryset_da_empresa(FatorPrecificacao.objects.all(), request.user), pk=pk
    )
    fator.delete()
    messages.success(request, "Fator removido.")
    return redirect("precificacao")
