from django import forms

from .models import ConfiguracaoPrecificacao, CustoFixo, FatorPrecificacao
from core.forms import ArqModelForm


class CustoFixoForm(ArqModelForm):
    class Meta:
        model = CustoFixo
        fields = ["descricao", "valor_mensal", "ativo"]


class ConfiguracaoPrecificacaoForm(ArqModelForm):
    class Meta:
        model = ConfiguracaoPrecificacao
        fields = [
            "horas_uteis_mes",
            "hora_tecnica_manual",
            "margem_seguranca_percent",
            "reserva_percent",
        ]
        labels = {
            "horas_uteis_mes": "Horas úteis por mês",
            "hora_tecnica_manual": "Hora técnica manual",
            "margem_seguranca_percent": "Margem de segurança (%)",
            "reserva_percent": "Reserva (%)",
        }


class FatorPrecificacaoForm(ArqModelForm):
    class Meta:
        model = FatorPrecificacao
        fields = ["nome", "percentual", "ativo"]
