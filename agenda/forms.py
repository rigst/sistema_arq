from django import forms

from core.forms import ArqModelForm
from core.tenancy import queryset_da_empresa
from crm.models import Cliente
from projetos.models import Projeto

from .models import Compromisso


class CompromissoForm(ArqModelForm):
    class Meta:
        model = Compromisso
        fields = ["titulo", "tipo", "inicio", "fim", "local", "cliente", "projeto", "observacoes"]
        widgets = {
            "inicio": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "fim": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["inicio"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["fim"].input_formats = ["%Y-%m-%dT%H:%M"]
        if user is not None:
            self.fields["cliente"].queryset = queryset_da_empresa(Cliente.objects.all(), user)
            self.fields["cliente"].required = False
            self.fields["projeto"].queryset = queryset_da_empresa(Projeto.objects.all(), user)
            self.fields["projeto"].required = False
