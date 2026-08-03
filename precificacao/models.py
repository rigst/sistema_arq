from decimal import Decimal

from django.db import models

from core.models import EmpresaModel, Rastreavel


class ConfiguracaoPrecificacao(EmpresaModel):
    """Parâmetros de precificação do escritório (um registro por empresa)."""

    horas_uteis_mes = models.PositiveIntegerField(
        default=160, help_text="Horas realmente trabalhadas no mês (base da hora técnica).",
        verbose_name="horas úteis por mês",
    )
    margem_seguranca_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("10.00"),
        help_text="Margem de segurança sobre as horas estimadas.",
        verbose_name="margem de segurança (%)",
    )
    imposto_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        help_text="Percentual estimado de impostos incidente sobre o serviço.",
        verbose_name="imposto (%)",
    )
    hora_tecnica_manual = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Se preenchida, é a hora técnica-base cobrada (sobrepõe o cálculo por custos). "
        "O valor por custos continua sendo o piso usado no cálculo de margem.",
        verbose_name="hora técnica manual",
    )

    class Meta:
        verbose_name = "configuração de precificação"
        verbose_name_plural = "configurações de precificação"

    def __str__(self):
        return f"Precificação ({self.horas_uteis_mes} h/mês)"


class FatorPrecificacao(EmpresaModel):
    """Variável de projeto que ajusta a hora técnica cobrada (ex.: urgência +30%,
    alta complexidade +25%, cliente recorrente -10%). Percentual pode ser negativo."""

    nome = models.CharField(max_length=80)
    percentual = models.DecimalField(
        max_digits=6, decimal_places=2,
        help_text="Ajuste sobre a hora técnica-base, em %. Aceita valores negativos.",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-percentual", "nome"]
        verbose_name = "fator de precificação"
        verbose_name_plural = "fatores de precificação"

    def __str__(self):
        sinal = "+" if self.percentual >= 0 else ""
        return f"{self.nome} ({sinal}{self.percentual}%)"


class CustoFixo(EmpresaModel, Rastreavel):
    """Custo mensal fixo do escritório (pró-labore, aluguel, energia, ...)."""

    descricao = models.CharField(max_length=150, verbose_name="descrição")
    valor_mensal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="valor mensal")
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-valor_mensal", "descricao"]
        verbose_name = "custo fixo"
        verbose_name_plural = "custos fixos"

    def __str__(self):
        return f"{self.descricao} — R$ {self.valor_mensal}"
