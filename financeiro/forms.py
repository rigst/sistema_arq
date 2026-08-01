from django import forms

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .models import Categoria, ContaBancaria, Lancamento
from core.forms import ArqForm, ArqModelForm


class LancamentoForm(ArqModelForm):
    class Meta:
        model = Lancamento
        fields = ["tipo", "conta", "categoria", "projeto", "descricao", "valor", "data", "status"]
        widgets = {"data": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["conta"].queryset = queryset_da_empresa(ContaBancaria.objects.all(), user)
            self.fields["categoria"].queryset = queryset_da_empresa(Categoria.objects.all(), user)
            self.fields["categoria"].required = False
            self.fields["projeto"].queryset = queryset_da_empresa(Projeto.objects.all(), user)
            self.fields["projeto"].required = False


class ContaBancariaForm(ArqModelForm):
    class Meta:
        model = ContaBancaria
        fields = ["nome", "saldo_inicial", "pessoal"]


class ImportarExtratoForm(ArqForm):
    conta = forms.ModelChoiceField(queryset=ContaBancaria.objects.none(), label="Conta")
    arquivo = forms.FileField(label="Extrato (OFX ou CSV)")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["conta"].queryset = queryset_da_empresa(ContaBancaria.objects.all(), user)
