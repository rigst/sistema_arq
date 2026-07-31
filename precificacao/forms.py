from django import forms

from .models import ConfiguracaoPrecificacao, CustoFixo, FatorPrecificacao


class CustoFixoForm(forms.ModelForm):
    class Meta:
        model = CustoFixo
        fields = ["descricao", "valor_mensal", "ativo"]


class ConfiguracaoPrecificacaoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoPrecificacao
        fields = [
            "horas_uteis_mes",
            "hora_tecnica_manual",
            "margem_seguranca_percent",
            "reserva_percent",
        ]


class FatorPrecificacaoForm(forms.ModelForm):
    class Meta:
        model = FatorPrecificacao
        fields = ["nome", "percentual", "ativo"]
