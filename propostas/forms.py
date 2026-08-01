from django import forms

from core.tenancy import queryset_da_empresa
from crm.models import Cliente

from .models import ItemProposta, Proposta
from core.forms import ArqModelForm

TIPO_CHOICES = [
    ("residencial", "Residencial"),
    ("comercial", "Comercial"),
    ("corporativo", "Corporativo"),
    ("interiores", "Interiores"),
]


class PropostaForm(ArqModelForm):
    tipo_projeto = forms.ChoiceField(choices=TIPO_CHOICES)

    class Meta:
        model = Proposta
        fields = ["titulo", "cliente", "tipo_projeto", "validade", "observacoes"]
        widgets = {
            "validade": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["cliente"].queryset = queryset_da_empresa(Cliente.objects.all(), user)


class ItemPropostaForm(ArqModelForm):
    class Meta:
        model = ItemProposta
        fields = ["descricao", "horas_estimadas"]
