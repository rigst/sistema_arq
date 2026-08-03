from django import forms

from .models import ConfiguracaoPrecificacao, CustoFixo, FatorPrecificacao
from core.forms import ArqModelForm


class CustoFixoForm(ArqModelForm):
    class Meta:
        model = CustoFixo
        fields = ["descricao", "valor_mensal"]
        widgets = {
            "descricao": forms.TextInput(attrs={"placeholder": "Ex.: Aluguel"}),
            "valor_mensal": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "placeholder": "0,00"}
            ),
        }


class ConfiguracaoPrecificacaoForm(ArqModelForm):
    class Meta:
        model = ConfiguracaoPrecificacao
        fields = [
            "horas_uteis_mes",
            "hora_tecnica_manual",
            "margem_seguranca_percent",
            "imposto_percent",
        ]
        labels = {
            "horas_uteis_mes": "Horas úteis por mês",
            "hora_tecnica_manual": "Hora técnica manual",
            "margem_seguranca_percent": "Margem de segurança (%)",
            "imposto_percent": "Imposto (%)",
        }
        widgets = {
            "horas_uteis_mes": forms.NumberInput(attrs={"min": "1", "step": "1"}),
            "hora_tecnica_manual": forms.NumberInput(
                attrs={"min": "0", "step": "0.01", "placeholder": "Automática pelos custos"}
            ),
            "margem_seguranca_percent": forms.NumberInput(
                attrs={"min": "0", "step": "0.01"}
            ),
            "imposto_percent": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }


class FatorPrecificacaoForm(ArqModelForm):
    class Meta:
        model = FatorPrecificacao
        fields = ["nome", "percentual"]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Urgência"}),
            "percentual": forms.NumberInput(attrs={"step": "0.01", "placeholder": "+20 ou -10"}),
        }
