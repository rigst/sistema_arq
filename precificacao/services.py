"""Serviços da cadeia de precificação — o núcleo de valor do sistema.

hora técnica = custos fixos mensais ÷ horas úteis no mês
preço da etapa = (hora técnica × horas estimadas com margem) + reserva + despesas
"""

from decimal import Decimal

from django.db.models import Sum

from .models import ConfiguracaoPrecificacao, CustoFixo

CEM = Decimal("100")


def obter_configuracao(grupo):
    config, _ = ConfiguracaoPrecificacao.objects.get_or_create(empresa=grupo)
    return config


def total_custos_fixos(grupo):
    total = (
        CustoFixo.objects.filter(empresa=grupo, ativo=True).aggregate(t=Sum("valor_mensal"))["t"]
    )
    return total or Decimal("0")


def calcular_hora_tecnica(grupo):
    """Valor da hora técnica do escritório. Retorna Decimal (0 se sem base)."""
    config = obter_configuracao(grupo)
    horas = Decimal(config.horas_uteis_mes or 0)
    if horas <= 0:
        return Decimal("0")
    return (total_custos_fixos(grupo) / horas).quantize(Decimal("0.01"))


def precificar_etapa(grupo, horas_estimadas, despesas_diretas=Decimal("0")):
    """Preço de uma etapa a partir das horas estimadas."""
    config = obter_configuracao(grupo)
    hora_tecnica = calcular_hora_tecnica(grupo)
    horas = Decimal(str(horas_estimadas or 0))
    despesas = Decimal(str(despesas_diretas or 0))

    horas_com_margem = horas * (Decimal("1") + config.margem_seguranca_percent / CEM)
    base = hora_tecnica * horas_com_margem
    com_reserva = base * (Decimal("1") + config.reserva_percent / CEM)
    total = (com_reserva + despesas).quantize(Decimal("0.01"))
    return {
        "hora_tecnica": hora_tecnica,
        "horas_com_margem": horas_com_margem.quantize(Decimal("0.01")),
        "subtotal": base.quantize(Decimal("0.01")),
        "despesas_diretas": despesas.quantize(Decimal("0.01")),
        "total": total,
    }
