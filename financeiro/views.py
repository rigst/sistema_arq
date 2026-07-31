from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import ContaBancariaForm, LancamentoForm
from .models import ContaBancaria, Lancamento
from .services import resumo_mensal


@login_required
def painel_financeiro(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)

    if request.method == "POST":
        form = LancamentoForm(request.POST, user=request.user)
        if form.is_valid():
            lancamento = form.save(commit=False)
            lancamento.empresa = grupo
            lancamento.criado_por = request.user
            lancamento.save()
            messages.success(request, "Lançamento registrado.")
            return redirect("financeiro_painel")
    else:
        form = LancamentoForm(user=request.user)

    lancamentos = queryset_da_empresa(
        Lancamento.objects.select_related("conta", "categoria", "projeto"), request.user
    )[:100]
    contas = queryset_da_empresa(ContaBancaria.objects.all(), request.user)

    saldos = []
    for conta in contas:
        entradas = conta.lancamentos.filter(tipo="entrada", status="realizado").aggregate(
            t=Sum("valor")
        )["t"] or Decimal("0")
        saidas = conta.lancamentos.filter(tipo="saida", status="realizado").aggregate(
            t=Sum("valor")
        )["t"] or Decimal("0")
        saldos.append({"conta": conta, "saldo": conta.saldo_inicial + entradas - saidas})

    return render(
        request,
        "financeiro/painel.html",
        {
            "form": form,
            "form_conta": ContaBancariaForm(),
            "lancamentos": lancamentos,
            "saldos": saldos,
            "tem_conta": contas.exists(),
            "resumo": resumo_mensal(grupo),
        },
    )


@require_POST
@login_required
def nova_conta(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    form = ContaBancariaForm(request.POST)
    if form.is_valid():
        conta = form.save(commit=False)
        conta.empresa = grupo
        conta.save()
        messages.success(request, "Conta criada.")
    else:
        messages.error(request, "Verifique os dados da conta.")
    return redirect("financeiro_painel")
