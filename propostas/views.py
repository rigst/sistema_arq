from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from precificacao.services import calcular_hora_tecnica, precificar_etapa
from projetos.models import Projeto, criar_etapas_padrao

from .forms import ItemPropostaForm, PropostaForm
from .models import ItemProposta, Proposta


@login_required
def lista_propostas(request):
    propostas = queryset_da_empresa(Proposta.objects.select_related("cliente"), request.user)
    return render(request, "propostas/lista.html", {"propostas": propostas})


@login_required
def nova_proposta(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    if request.method == "POST":
        form = PropostaForm(request.POST, user=request.user)
        if form.is_valid():
            proposta = form.save(commit=False)
            proposta.empresa = grupo
            proposta.criado_por = request.user
            proposta.hora_tecnica_aplicada = calcular_hora_tecnica(grupo)
            proposta.save()
            messages.success(request, "Proposta criada. Adicione os ambientes/etapas.")
            return redirect("proposta_detalhe", pk=proposta.pk)
    else:
        form = PropostaForm(user=request.user)
    return render(request, "propostas/form.html", {"form": form})


@login_required
def detalhe_proposta(request, pk):
    proposta = get_object_or_404(
        queryset_da_empresa(Proposta.objects.select_related("cliente"), request.user), pk=pk
    )
    return render(
        request,
        "propostas/detalhe.html",
        {"proposta": proposta, "itens": proposta.itens.all(), "form_item": ItemPropostaForm()},
    )


@require_POST
@login_required
def adicionar_item(request, pk):
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    form = ItemPropostaForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        calc = precificar_etapa(proposta.empresa, item.horas_estimadas)
        item.proposta = proposta
        item.empresa = proposta.empresa
        item.valor = calc["total"]
        item.ordem = proposta.itens.count()
        item.save()
        messages.success(request, "Item precificado e adicionado.")
    else:
        messages.error(request, "Informe descrição e horas.")
    return redirect("proposta_detalhe", pk=proposta.pk)


@require_POST
@login_required
def remover_item(request, pk):
    item = get_object_or_404(queryset_da_empresa(ItemProposta.objects.all(), request.user), pk=pk)
    proposta_pk = item.proposta_id
    item.delete()
    return redirect("proposta_detalhe", pk=proposta_pk)


@require_POST
@login_required
def aprovar_proposta(request, pk):
    """Aprovar gera o projeto (com etapas) — elo Proposta → Projeto da jornada."""
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    if proposta.projeto_gerado_id:
        messages.info(request, "Esta proposta já gerou um projeto.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    with transaction.atomic():
        projeto = Projeto.objects.create(
            empresa=proposta.empresa,
            nome=proposta.titulo,
            cliente=proposta.cliente,
            tipo=proposta.tipo_projeto,
            valor_contratado=proposta.valor_total,
            data_inicio=timezone.localdate(),
            criado_por=request.user,
            origem_tipo="proposta",
            origem_id=proposta.pk,
        )
        criar_etapas_padrao(projeto)
        proposta.status = "aprovada"
        proposta.projeto_gerado = projeto
        proposta.save(update_fields=["status", "projeto_gerado"])
        # Move o cliente para "ganho" no funil.
        proposta.cliente.fase = "ganho"
        proposta.cliente.save(update_fields=["fase"])

    messages.success(request, "Proposta aprovada. Projeto criado com as etapas.")
    return redirect("projeto_detalhe", pk=projeto.pk)
