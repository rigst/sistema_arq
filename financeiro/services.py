"""Serviços financeiros: margem por projeto e resumo mensal.

margem = valor contratado − custo das horas reais − despesas diretas do projeto
custo das horas = horas apontadas no projeto × hora técnica do escritório
"""

from decimal import Decimal

from django.db.models import Sum

from precificacao.services import calcular_hora_tecnica

CEM = Decimal("100")


def _soma_horas_projeto(projeto):
    from tarefas.models import ApontamentoHora

    total = Decimal("0")
    apontamentos = ApontamentoHora.objects.filter(empresa=projeto.empresa, projeto=projeto)
    for ap in apontamentos:
        total += ap.horas
    return total


def calcular_margem_projeto(projeto):
    from .models import Lancamento

    hora_tecnica = calcular_hora_tecnica(projeto.empresa)
    horas = _soma_horas_projeto(projeto)
    custo_horas = (hora_tecnica * horas).quantize(Decimal("0.01"))

    despesas = (
        Lancamento.objects.filter(empresa=projeto.empresa, projeto=projeto, tipo="saida")
        .aggregate(t=Sum("valor"))["t"]
        or Decimal("0")
    )
    contratado = Decimal(projeto.valor_contratado or 0)
    margem = (contratado - custo_horas - despesas).quantize(Decimal("0.01"))
    percent = (margem / contratado * CEM).quantize(Decimal("0.1")) if contratado else Decimal("0")
    return {
        "hora_tecnica": hora_tecnica,
        "horas": horas,
        "custo_horas": custo_horas,
        "despesas": despesas,
        "contratado": contratado,
        "margem": margem,
        "margem_percent": percent,
    }


def dre(grupo, ano, mes):
    """Demonstração de resultado do mês: realizado agrupado por categoria."""
    from .models import Categoria, Lancamento

    qs = Lancamento.objects.filter(
        empresa=grupo, status="realizado", data__year=ano, data__month=mes
    )

    def _por_categoria(tipo):
        linhas = []
        agrup = (
            qs.filter(tipo=tipo)
            .values("categoria__nome")
            .annotate(total=Sum("valor"))
            .order_by("-total")
        )
        for row in agrup:
            linhas.append({"categoria": row["categoria__nome"] or "Sem categoria", "total": row["total"]})
        return linhas

    entradas = _por_categoria("entrada")
    saidas = _por_categoria("saida")
    total_entradas = sum((l["total"] for l in entradas), Decimal("0"))
    total_saidas = sum((l["total"] for l in saidas), Decimal("0"))
    return {
        "ano": ano,
        "mes": mes,
        "entradas": entradas,
        "saidas": saidas,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "resultado": total_entradas - total_saidas,
    }


def resumo_mensal(grupo, ano=None, mes=None):
    from django.utils import timezone

    from .models import Lancamento

    hoje = timezone.localdate()
    ano = ano or hoje.year
    mes = mes or hoje.month
    qs = Lancamento.objects.filter(
        empresa=grupo, status="realizado", data__year=ano, data__month=mes
    )
    entradas = qs.filter(tipo="entrada").aggregate(t=Sum("valor"))["t"] or Decimal("0")
    saidas = qs.filter(tipo="saida").aggregate(t=Sum("valor"))["t"] or Decimal("0")
    return {"ano": ano, "mes": mes, "entradas": entradas, "saidas": saidas, "saldo": entradas - saidas}
