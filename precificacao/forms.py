from django import forms

from .models import ConfiguracaoPrecificacao, CustoFixo


class CustoFixoForm(forms.ModelForm):
    class Meta:
        model = CustoFixo
        fields = ["descricao", "valor_mensal", "ativo"]


class ConfiguracaoPrecificacaoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoPrecificacao
        fields = ["horas_uteis_mes", "margem_seguranca_percent", "reserva_percent"]
