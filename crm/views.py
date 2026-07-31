from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import ClienteForm, InteracaoForm
from .models import Cliente


@login_required
def lista_clientes(request):
    clientes = queryset_da_empresa(Cliente.objects.all(), request.user)
    fase = request.GET.get("fase", "")
    if fase:
        clientes = clientes.filter(fase=fase)
    return render(
        request,
        "crm/lista.html",
        {"clientes": clientes, "fases": Cliente.FASE_CHOICES, "fase_ativa": fase},
    )


@login_required
def novo_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.empresa = obter_grupo_empresa_ou_erro(request.user)
            cliente.criado_por = request.user
            cliente.save()
            messages.success(request, "Cliente cadastrado.")
            return redirect("crm_detalhe", pk=cliente.pk)
    else:
        form = ClienteForm()
    return render(request, "crm/form.html", {"form": form, "titulo": "Novo cliente"})


@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(queryset_da_empresa(Cliente.objects.all(), request.user), pk=pk)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente atualizado.")
            return redirect("crm_detalhe", pk=cliente.pk)
    else:
        form = ClienteForm(instance=cliente)
    return render(
        request, "crm/form.html", {"form": form, "titulo": f"Editar {cliente.nome}"}
    )


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
        },
    )


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
