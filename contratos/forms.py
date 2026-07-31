from django import forms

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .models import AlteracaoEscopo, Contrato, Documento


class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ["projeto", "titulo", "numero", "valor_total", "data_assinatura", "status", "observacoes"]
        widgets = {
            "data_assinatura": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["projeto"].queryset = queryset_da_empresa(Projeto.objects.all(), user)


class GerarParcelasForm(forms.Form):
    quantidade = forms.IntegerField(min_value=1, max_value=60, initial=1, label="Nº de parcelas")
    primeira_data = forms.DateField(
        label="1º vencimento", widget=forms.DateInput(attrs={"type": "date"})
    )
    intervalo_dias = forms.IntegerField(min_value=1, initial=30, label="Intervalo (dias)")


class AlteracaoEscopoForm(forms.ModelForm):
    class Meta:
        model = AlteracaoEscopo
        fields = ["tipo", "descricao", "valor_delta"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 2})}


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["titulo", "arquivo"]
