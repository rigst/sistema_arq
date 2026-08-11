from django import forms
from django.utils import timezone

from core.forms import ArqForm, ArqModelForm, campo_relacionado
from core.tenancy import queryset_da_empresa
from core.uploads import validar_extrato

from .models import ContaBancaria, Lancamento


class LancamentoForm(ArqModelForm):
    class Meta:
        model = Lancamento
        fields = ["tipo", "conta", "descricao", "valor", "data", "status"]
        widgets = {"data": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields["tipo"].initial = "saida"
            self.fields["data"].initial = timezone.localdate()
            self.fields["status"].initial = "realizado"
        if user is not None:
            contas = queryset_da_empresa(ContaBancaria.objects.all(), user)
            campo_relacionado(self, "conta").queryset = contas
            if not self.is_bound:
                primeira_conta = contas.first()
                if primeira_conta is not None:
                    self.fields["conta"].initial = primeira_conta.pk


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
            campo_relacionado(self, "conta").queryset = queryset_da_empresa(
                ContaBancaria.objects.all(), user
            )
