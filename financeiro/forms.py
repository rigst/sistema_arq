from django import forms
from django.utils import timezone

from core.tenancy import queryset_da_empresa
from core.uploads import validar_extrato
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
        if not self.is_bound:
            self.fields["tipo"].initial = "saida"
            self.fields["data"].initial = timezone.localdate()
            self.fields["status"].initial = "realizado"
        if user is not None:
            self.fields["conta"].queryset = queryset_da_empresa(ContaBancaria.objects.all(), user)
            if not self.is_bound:
                primeira_conta = self.fields["conta"].queryset.first()
                if primeira_conta is not None:
                    self.fields["conta"].initial = primeira_conta.pk
            self.fields["categoria"].queryset = queryset_da_empresa(Categoria.objects.all(), user)
            self.fields["categoria"].required = False
            self.fields["categoria"].empty_label = "Sem categoria"
            self.fields["projeto"].queryset = queryset_da_empresa(Projeto.objects.all(), user)
            self.fields["projeto"].required = False
            self.fields["projeto"].empty_label = "Sem projeto"


class ContaBancariaForm(ArqModelForm):
    class Meta:
        model = ContaBancaria
        fields = ["nome", "saldo_inicial", "pessoal"]


class ImportarExtratoForm(ArqForm):
    conta = forms.ModelChoiceField(queryset=ContaBancaria.objects.none(), label="Conta")
    arquivo = forms.FileField(label="Extrato (OFX ou CSV)", validators=[validar_extrato])

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["conta"].queryset = queryset_da_empresa(ContaBancaria.objects.all(), user)
