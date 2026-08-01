from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import FornecedorForm
from .models import Fornecedor


def _meus(user):
    return queryset_da_empresa(Fornecedor.objects.all(), user)


@login_required
def lista(request):
    categoria = request.GET.get("categoria", "")
    fornecedores = _meus(request.user)
    if categoria:
        fornecedores = fornecedores.filter(categoria=categoria)

    # Categorias que o escritório realmente usa — não a lista inteira de choices.
    usadas = set(_meus(request.user).values_list("categoria", flat=True))
    categorias = [(v, r) for v, r in Fornecedor.CATEGORIA_CHOICES if v in usadas]

    return render(
        request,
        "fornecedores/lista.html",
        {
            "fornecedores": fornecedores,
            "categorias": categorias,
            "categoria_ativa": categoria,
        },
    )


@login_required
def novo(request):
    return _editar(request, None)


@login_required
def editar(request, pk):
    fornecedor = get_object_or_404(_meus(request.user), pk=pk)
    return _editar(request, fornecedor)


def _editar(request, fornecedor):
    if request.method == "POST":
        form = FornecedorForm(request.POST, instance=fornecedor)
        if form.is_valid():
            novo_fornecedor = form.save(commit=False)
            if fornecedor is None:
                novo_fornecedor.empresa = obter_grupo_empresa_ou_erro(request.user)
                novo_fornecedor.criado_por = request.user
            novo_fornecedor.save()
            messages.success(request, "Fornecedor salvo.")
            return redirect("fornecedores_lista")
    else:
        form = FornecedorForm(instance=fornecedor)
    return render(
        request, "fornecedores/form.html", {"form": form, "fornecedor": fornecedor}
    )
