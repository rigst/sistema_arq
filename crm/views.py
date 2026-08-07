from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import ClienteForm, InteracaoForm
from .models import Cliente


@login_required
def lista_clientes(request):
    todos = queryset_da_empresa(Cliente.objects.all(), request.user)
    mostrando_inativos = request.GET.get("inativos") == "1"
    clientes = todos.filter(ativo=not mostrando_inativos)
    fase = request.GET.get("fase", "")
    if fase:
        clientes = clientes.filter(fase=fase)
    clientes = list(clientes)
    return render(
        request,
        "crm/lista.html",
        {
            "clientes": clientes,
            "clientes_com_form": [(cliente, ClienteForm(instance=cliente)) for cliente in clientes],
            "form_cliente": ClienteForm(),
            "fases": Cliente.FASE_CHOICES,
            "fase_ativa": fase,
            "mostrando_inativos": mostrando_inativos,
            "total_inativos": todos.filter(ativo=False).count(),
        },
    )


@require_POST
@login_required
def novo_cliente(request):
    form = ClienteForm(request.POST)
    if form.is_valid():
        cliente = form.save(commit=False)
        cliente.empresa = obter_grupo_empresa_ou_erro(request.user)
        cliente.criado_por = request.user
        cliente.ativo = True
        cliente.save()
        messages.success(request, "Cliente cadastrado.")
    else:
        messages.error(request, "Confira os dados do cliente.")
    return redirect("crm_lista")


@require_POST
@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(queryset_da_empresa(Cliente.objects.all(), request.user), pk=pk)
    form = ClienteForm(request.POST, instance=cliente)
    if form.is_valid():
        form.save()
        messages.success(request, "Cliente atualizado.")
    else:
        messages.error(request, "Confira os dados do cliente.")
    return redirect("crm_lista")


@login_required
def detalhe_cliente(request, pk):
    cliente = get_object_or_404(queryset_da_empresa(Cliente.objects.all(), request.user), pk=pk)
    return render(
        request,
        "crm/detalhe.html",
        {
            "cliente": cliente,
            "interacoes": cliente.interacoes.all(),
            "form_interacao": InteracaoForm(),
            "form_cliente": ClienteForm(instance=cliente),
        },
    )


@require_POST
@login_required
def remover_cliente(request, pk):
    cliente = get_object_or_404(queryset_da_empresa(Cliente.objects.all(), request.user), pk=pk)
    try:
        cliente.delete()
        messages.success(request, "Cliente excluído.")
    except ProtectedError:
        messages.error(
            request,
            "Este cliente possui projetos ou propostas vinculados e não pode ser excluído.",
        )
    return redirect("crm_lista")


@require_POST
@login_required
def adicionar_interacao(request, pk):
    cliente = get_object_or_404(queryset_da_empresa(Cliente.objects.all(), request.user), pk=pk)
    form = InteracaoForm(request.POST)
    if form.is_valid():
        interacao = form.save(commit=False)
        interacao.cliente = cliente
        interacao.empresa = cliente.empresa
        interacao.autor = request.user
        interacao.save()
        messages.success(request, "Interação registrada.")
    else:
        messages.error(request, "Descreva a interação.")
    return redirect("crm_detalhe", pk=cliente.pk)
