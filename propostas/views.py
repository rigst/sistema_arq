from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from decimal import Decimal, InvalidOperation

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from precificacao.models import FatorPrecificacao
from precificacao.services import aplicar_fatores, hora_tecnica_base, precificar_etapa
from projetos.models import Projeto, criar_etapas_padrao

from .forms import ItemPropostaForm, PropostaForm
from .models import ItemProposta, Proposta


def _reprecificar_itens(proposta):
    """Recalcula o valor de todos os itens com a hora técnica atual da proposta."""
    for item in proposta.itens.all():
        calc = precificar_etapa(
            proposta.empresa, item.horas_estimadas, hora_tecnica=proposta.hora_tecnica_aplicada
        )
        item.valor = calc["total"]
        item.save(update_fields=["valor"])


@login_required
def lista_propostas(request):
    propostas = queryset_da_empresa(Proposta.objects.select_related("cliente"), request.user)
    return render(request, "propostas/lista.html", {"propostas": propostas})


@login_required
def nova_proposta(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    projeto = projeto_do_pedido(request)
    if request.method == "POST":
        form = PropostaForm(request.POST, user=request.user, projeto=projeto)
        if form.is_valid():
            proposta = form.save(commit=False)
            proposta.empresa = grupo
            proposta.criado_por = request.user
            proposta.hora_tecnica_aplicada = hora_tecnica_base(grupo)
            if projeto is not None:
                # Fecha o laço: a proposta nascida de um projeto aponta para ele,
                # senão o roteiro continuaria dizendo que falta proposta.
                proposta.projeto_gerado = projeto
            proposta.save()
            messages.success(
                request, "Proposta criada. Ajuste a hora técnica e adicione os ambientes."
            )
            return redirect("proposta_detalhe", pk=proposta.pk)
    else:
        form = PropostaForm(user=request.user, projeto=projeto)
    return render(request, "propostas/form.html", {"form": form, "projeto": projeto})


@login_required
def detalhe_proposta(request, pk):
    proposta = get_object_or_404(
        queryset_da_empresa(Proposta.objects.select_related("cliente"), request.user), pk=pk
    )
    fatores = queryset_da_empresa(FatorPrecificacao.objects.filter(ativo=True), request.user)
    selecionados = set(proposta.fatores.values_list("pk", flat=True))
    return render(
        request,
        "propostas/detalhe.html",
        {
            "proposta": proposta,
            "itens": proposta.itens.all(),
            "form_item": ItemPropostaForm(),
            "base": hora_tecnica_base(proposta.empresa),
            "fatores": fatores,
            "fatores_selecionados": selecionados,
        },
    )


@require_POST
@login_required
def definir_hora_tecnica(request, pk):
    """Usuário escolhe a hora técnica da proposta: valor manual livre e/ou fatores
    de projeto aplicados sobre a hora-base. Reprecifica os itens existentes."""
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    if proposta.projeto_gerado_id:
        messages.info(request, "Proposta já aprovada; a hora técnica está travada.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    fatores_ids = request.POST.getlist("fatores")
    fatores = list(
        queryset_da_empresa(FatorPrecificacao.objects.all(), request.user).filter(pk__in=fatores_ids)
    )
    proposta.fatores.set(fatores)

    valor_manual = request.POST.get("valor_manual", "").strip().replace(",", ".")
    if valor_manual:
        try:
            proposta.hora_tecnica_aplicada = Decimal(valor_manual)
        except (InvalidOperation, ValueError):
            messages.error(request, "Valor de hora técnica inválido.")
            return redirect("proposta_detalhe", pk=proposta.pk)
    else:
        proposta.hora_tecnica_aplicada = aplicar_fatores(
            hora_tecnica_base(proposta.empresa), fatores
        )

    proposta.save(update_fields=["hora_tecnica_aplicada"])
    _reprecificar_itens(proposta)
    messages.success(
        request, f"Hora técnica desta proposta: R$ {proposta.hora_tecnica_aplicada}."
    )
    return redirect("proposta_detalhe", pk=proposta.pk)


@require_POST
@login_required
def adicionar_item(request, pk):
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    form = ItemPropostaForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        calc = precificar_etapa(
            proposta.empresa, item.horas_estimadas, hora_tecnica=proposta.hora_tecnica_aplicada
        )
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


@login_required
def proposta_pdf(request, pk):
    from django.utils import timezone

    from core.pdf import render_pdf

    proposta = get_object_or_404(
        queryset_da_empresa(Proposta.objects.select_related("cliente"), request.user), pk=pk
    )
    return render_pdf(
        "pdf/proposta.html",
        {
            "proposta": proposta,
            "itens": proposta.itens.all(),
            "empresa_nome": request.user.nome_empresa,
            "hoje": timezone.now(),
        },
        filename=f"proposta-{proposta.pk}.pdf",
    )


@require_POST
@login_required
def aprovar_proposta(request, pk):
    """Aprovar gera o projeto (com etapas) — elo Proposta → Projeto da jornada."""
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    if proposta.projeto_gerado_id:
        messages.info(request, "Esta proposta já gerou um projeto.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    horas_estimadas = sum(
        (item.horas_estimadas for item in proposta.itens.all()), Decimal("0")
    )
    with transaction.atomic():
        projeto = Projeto.objects.create(
            empresa=proposta.empresa,
            nome=proposta.titulo,
            cliente=proposta.cliente,
            tipo=proposta.tipo_projeto,
            valor_contratado=proposta.valor_total,
            horas_estimadas=horas_estimadas,
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
