"""Serviços da cadeia de precificação — o núcleo de valor do sistema.

- custo_hora (piso): custos fixos mensais ÷ horas úteis no mês. Usado na MARGEM.
- hora técnica-base cobrada: valor manual (se definido) ou o custo. Ponto de partida.
- hora técnica aplicada: base ajustada pelas variáveis do projeto (fatores) ou um
  valor escolhido livremente pelo usuário.
- imposto é descontado da receita; lucro previsto = receita líquida − custo operacional.
- preço da etapa = horas cobradas + despesas diretas (imposto não é somado ao cliente).
"""

from decimal import Decimal

from django.db.models import Sum

from .models import ConfiguracaoPrecificacao, CustoFixo

CEM = Decimal("100")


def obter_configuracao(grupo):
    config, _ = ConfiguracaoPrecificacao.objects.get_or_create(empresa=grupo)
    return config


def total_custos_fixos(grupo):
    total = CustoFixo.objects.filter(empresa=grupo, ativo=True).aggregate(t=Sum("valor_mensal"))[
        "t"
    ]
    return total or Decimal("0")


def custo_hora(grupo):
    """Piso de custo da hora (custos fixos ÷ horas úteis). Base da margem."""
    config = obter_configuracao(grupo)
    horas = Decimal(config.horas_uteis_mes or 0)
    if horas <= 0:
        return Decimal("0")
    return (total_custos_fixos(grupo) / horas).quantize(Decimal("0.01"))


# Mantido para compatibilidade: a margem usa o custo real da hora.
def calcular_hora_tecnica(grupo):
    return custo_hora(grupo)


def hora_tecnica_base(grupo):
    """Hora técnica-base cobrada: valor manual, se definido; senão, o custo."""
    config = obter_configuracao(grupo)
    if config.hora_tecnica_manual:
        return Decimal(config.hora_tecnica_manual)
    return custo_hora(grupo)


def aplicar_fatores(base, fatores):
    """Aplica um conjunto de fatores (percentuais somados) sobre a base."""
    soma = sum((Decimal(f.percentual) for f in fatores), Decimal("0"))
    return (Decimal(base) * (Decimal("1") + soma / CEM)).quantize(Decimal("0.01"))


def precificar_etapa(grupo, horas_estimadas, hora_tecnica=None, despesas_diretas=Decimal("0")):
    """Preço de uma etapa. `hora_tecnica` permite usar um valor escolhido; se None,
    usa a hora técnica-base do escritório."""
    config = obter_configuracao(grupo)
    ht = Decimal(str(hora_tecnica)) if hora_tecnica is not None else hora_tecnica_base(grupo)
    horas = Decimal(str(horas_estimadas or 0))
    despesas = Decimal(str(despesas_diretas or 0))

    horas_com_margem = horas * (Decimal("1") + config.margem_seguranca_percent / CEM)
    base = ht * horas_com_margem
    imposto = base * config.imposto_percent / CEM
    receita_liquida = base - imposto
    custo_operacional = custo_hora(grupo) * horas_com_margem
    lucro = receita_liquida - custo_operacional
    total = (base + despesas).quantize(Decimal("0.01"))
    return {
        "hora_tecnica": ht,
        "horas_com_margem": horas_com_margem.quantize(Decimal("0.01")),
        "subtotal": base.quantize(Decimal("0.01")),
        "imposto": imposto.quantize(Decimal("0.01")),
        "receita_liquida": receita_liquida.quantize(Decimal("0.01")),
        "custo_operacional": custo_operacional.quantize(Decimal("0.01")),
        "lucro_previsto": lucro.quantize(Decimal("0.01")),
        "despesas_diretas": despesas.quantize(Decimal("0.01")),
        "total": total,
    }
