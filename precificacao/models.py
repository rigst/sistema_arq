from decimal import Decimal

from django.db import models

from core.models import EmpresaModel, Rastreavel


class ConfiguracaoPrecificacao(EmpresaModel):
    """Parâmetros de precificação do escritório (um registro por empresa)."""

    horas_uteis_mes = models.PositiveIntegerField(
        default=160, help_text="Horas realmente trabalhadas no mês (base da hora técnica)."
    )
    margem_seguranca_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("10.00"),
        help_text="Margem de segurança sobre as horas estimadas.",
    )
    reserva_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("20.00"),
        help_text="Reserva do escritório (impostos, reinvestimento, imprevistos).",
    )

    class Meta:
        verbose_name = "configuração de precificação"
        verbose_name_plural = "configurações de precificação"

    def __str__(self):
        return f"Precificação ({self.horas_uteis_mes} h/mês)"


class CustoFixo(EmpresaModel, Rastreavel):
    """Custo mensal fixo do escritório (pró-labore, aluguel, energia, ...)."""

    descricao = models.CharField(max_length=150)
    valor_mensal = models.DecimalField(max_digits=12, decimal_places=2)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-valor_mensal", "descricao"]
        verbose_name = "custo fixo"
        verbose_name_plural = "custos fixos"

    def __str__(self):
        return f"{self.descricao} — R$ {self.valor_mensal}"
