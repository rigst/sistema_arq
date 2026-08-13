from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_safe

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from projetos.models import Projeto

from .forms import ItemOrcamentoForm, OrcamentoForm
from .models import ItemOrcamento, Orcamento


def _meus(user):
    return queryset_da_empresa(Orcamento.objects.select_related("projeto"), user)


@require_safe
@login_required
def lista(request):
    orcamentos = _meus(request.user).prefetch_related("itens")
    projeto = projeto_do_pedido(request)
    if projeto is not None:
        orcamentos = orcamentos.filter(projeto=projeto)
    return render(request, "orcamentos/lista.html", {"orcamentos": orcamentos, "projeto": projeto})


# POST, e não GET: a view cria um orçamento (e revisa o anterior) a cada
# chamada. Como link, qualquer prefetch do navegador ou varredura de robô
# criava versão fantasma, e o botão não tinha proteção de CSRF.
@require_POST
@login_required
def novo(request, projeto_pk):
    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.all(), request.user), pk=projeto_pk
    )
    grupo = obter_grupo_empresa_ou_erro(request.user)
    # Uma revisão nasce como cópia da anterior: reorçar do zero a cada versão
    # é o que faz o arquiteto desistir de manter o orçamento atualizado.
    anterior = projeto.orcamentos.order_by("-criado_em").first()
    orcamento = Orcamento.objects.create(
        projeto=projeto,
        empresa=grupo,
        criado_por=request.user,
        bdi_percent=anterior.bdi_percent if anterior else 0,
        versao=str(projeto.orcamentos.count() + 1),
    )
    if anterior:
        ItemOrcamento.objects.bulk_create(
            [
                ItemOrcamento(
                    orcamento=orcamento,
                    empresa=grupo,
                    ambiente=item.ambiente,
                    categoria=item.categoria,
                    descricao=item.descricao,
                    unidade=item.unidade,
                    quantidade=item.quantidade,
                    valor_unitario=item.valor_unitario,
                    fornecedor=item.fornecedor,
                    observacoes=item.observacoes,
                    ordem=item.ordem,
                )
                for item in anterior.itens.all()
            ]
        )
        anterior.status = "revisado"
        anterior.save(update_fields=["status"])
        messages.success(
            request, f"Versão {orcamento.versao} criada a partir da anterior. Ajuste o que mudou."
        )
    else:
        messages.success(request, "Orçamento criado. Comece lançando os itens.")
    return redirect("orcamento_detalhe", pk=orcamento.pk)


@login_required
def detalhe(request, pk):
    orcamento = get_object_or_404(_meus(request.user), pk=pk)

    if request.method == "POST":
        form = OrcamentoForm(request.POST, instance=orcamento)
        if form.is_valid():
            form.save()
            messages.success(request, "Orçamento salvo.")
            return redirect("orcamento_detalhe", pk=orcamento.pk)
    else:
        form = OrcamentoForm(instance=orcamento)

    return render(
        request,
        "orcamentos/detalhe.html",
        {
            "orcamento": orcamento,
            "form": form,
            "form_item": ItemOrcamentoForm(user=request.user),
            "itens": orcamento.itens.select_related("fornecedor"),
            "resumo": orcamento.por_categoria(),
        },
    )


@require_POST
@login_required
def adicionar_item(request, pk):
    orcamento = get_object_or_404(_meus(request.user), pk=pk)
    form = ItemOrcamentoForm(request.POST, user=request.user)
    if form.is_valid():
        item = form.save(commit=False)
        item.orcamento = orcamento
        item.empresa = orcamento.empresa
        item.ordem = orcamento.itens.count()
        item.save()
        messages.success(request, "Item lançado.")
    else:
        messages.error(request, "Confira os campos do item.")
    return redirect("orcamento_detalhe", pk=orcamento.pk)


@require_POST
@login_required
def remover_item(request, pk):
    item = get_object_or_404(queryset_da_empresa(ItemOrcamento.objects.all(), request.user), pk=pk)
    orcamento_pk = item.orcamento_id
    item.delete()
    return redirect("orcamento_detalhe", pk=orcamento_pk)


@require_POST
@login_required
def registrar_realizado(request, pk):
    """Fecha o item com o valor efetivamente contratado, alimentando o desvio."""
    item = get_object_or_404(queryset_da_empresa(ItemOrcamento.objects.all(), request.user), pk=pk)
    bruto = (request.POST.get("valor_realizado") or "").replace(".", "").replace(",", ".").strip()
    if bruto == "":
        item.valor_realizado = None
    else:
        try:
            from decimal import Decimal, InvalidOperation

            item.valor_realizado = Decimal(bruto)
        except (InvalidOperation, ValueError):
            messages.error(request, "Valor realizado inválido.")
            return redirect("orcamento_detalhe", pk=item.orcamento_id)
    item.save(update_fields=["valor_realizado"])
    return redirect("orcamento_detalhe", pk=item.orcamento_id)
