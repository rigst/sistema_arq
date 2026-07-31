import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .extrato import conciliar, parse_csv, parse_ofx
from .forms import ContaBancariaForm, ImportarExtratoForm, LancamentoForm
from .models import ContaBancaria, Lancamento
from .services import dre, resumo_mensal


def _periodo(request):
    hoje = timezone.localdate()
    try:
        ano = int(request.GET.get("ano", hoje.year))
        mes = int(request.GET.get("mes", hoje.month))
    except (TypeError, ValueError):
        ano, mes = hoje.year, hoje.month
    return ano, mes


@login_required
def dre_view(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    ano, mes = _periodo(request)
    return render(request, "financeiro/dre.html", {"dre": dre(grupo, ano, mes), "ano": ano, "mes": mes})


@login_required
def dre_csv(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    ano, mes = _periodo(request)
    dados = dre(grupo, ano, mes)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="dre-{ano}-{mes:02d}.csv"'
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["DRE", f"{mes:02d}/{ano}"])
    writer.writerow([])
    writer.writerow(["Tipo", "Categoria", "Valor"])
    for l in dados["entradas"]:
        writer.writerow(["Entrada", l["categoria"], l["total"]])
    for l in dados["saidas"]:
        writer.writerow(["Saída", l["categoria"], l["total"]])
    writer.writerow([])
    writer.writerow(["Total entradas", "", dados["total_entradas"]])
    writer.writerow(["Total saídas", "", dados["total_saidas"]])
    writer.writerow(["Resultado", "", dados["resultado"]])
    return response


@login_required
def importar_extrato(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    resultado = None
    if request.method == "POST":
        form = ImportarExtratoForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            arquivo = form.cleaned_data["arquivo"]
            conta = form.cleaned_data["conta"]
            nome = arquivo.name.lower()
            try:
                if nome.endswith(".ofx"):
                    transacoes = parse_ofx(arquivo)
                else:
                    transacoes = parse_csv(arquivo)
            except Exception:  # noqa: BLE001
                messages.error(request, "Não foi possível ler o arquivo. Confira o formato (OFX ou CSV).")
                return redirect("financeiro_importar")
            if not transacoes:
                messages.error(request, "Nenhuma transação encontrada no arquivo.")
                return redirect("financeiro_importar")
            conciliados, criados = conciliar(grupo, conta, transacoes)
            resultado = {"total": len(transacoes), "conciliados": conciliados, "criados": criados}
            messages.success(
                request,
                f"{len(transacoes)} transações: {conciliados} conciliadas e {criados} criadas.",
            )
    else:
        form = ImportarExtratoForm(user=request.user)
    return render(request, "financeiro/importar.html", {"form": form, "resultado": resultado})


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
