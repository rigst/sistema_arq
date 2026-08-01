from django import forms

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .models import AlteracaoEscopo, Contrato, Documento, ModeloContrato
from core.forms import ArqForm, ArqModelForm


class ContratoForm(ArqModelForm):
    class Meta:
        model = Contrato
        fields = ["projeto", "titulo", "numero", "valor_total", "data_assinatura", "status", "observacoes"]
        widgets = {
            "data_assinatura": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, projeto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["projeto"].queryset = queryset_da_empresa(Projeto.objects.all(), user)
        if projeto is not None:
            self.fields["projeto"].initial = projeto.pk
            self.fields["projeto"].disabled = True
            self.fields["titulo"].initial = f"Contrato — {projeto.nome}"
            if projeto.valor_contratado:
                self.fields["valor_total"].initial = projeto.valor_contratado


class GerarParcelasForm(ArqForm):
    quantidade = forms.IntegerField(min_value=1, max_value=60, initial=1, label="Nº de parcelas")
    primeira_data = forms.DateField(
        label="1º vencimento", widget=forms.DateInput(attrs={"type": "date"})
    )
    intervalo_dias = forms.IntegerField(min_value=1, initial=30, label="Intervalo (dias)")


class AlteracaoEscopoForm(ArqModelForm):
    class Meta:
        model = AlteracaoEscopo
        fields = ["tipo", "descricao", "valor_delta"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 2})}


class DocumentoForm(ArqModelForm):
    class Meta:
        model = Documento
        fields = ["titulo", "arquivo"]


class ModeloContratoForm(ArqModelForm):
    class Meta:
        model = ModeloContrato
        fields = ["nome", "descricao", "corpo", "padrao", "ativo"]
        widgets = {"corpo": forms.Textarea(attrs={"rows": 20, "spellcheck": "true"})}
