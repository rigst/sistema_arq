from typing import cast

from django import forms

from core.forms import ArqModelForm, campo_relacionado
from core.tenancy import queryset_da_empresa
from crm.models import Cliente
from projetos.models import Projeto

from .models import Compromisso

# O widget datetime-local do HTML só aceita este formato; usado na saída
# (format) e na entrada (input_formats), que precisam casar.
FORMATO_DATETIME_LOCAL = "%Y-%m-%dT%H:%M"


class CompromissoForm(ArqModelForm):
    class Meta:
        model = Compromisso
        fields = ["titulo", "tipo", "inicio", "fim", "local", "cliente", "projeto", "observacoes"]
        widgets = {
            "inicio": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format=FORMATO_DATETIME_LOCAL
            ),
            "fim": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format=FORMATO_DATETIME_LOCAL
            ),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # input_formats existe em DateTimeField, não no Field genérico que a
        # dict `fields` declara.
        for nome in ("inicio", "fim"):
            cast(forms.DateTimeField, self.fields[nome]).input_formats = [FORMATO_DATETIME_LOCAL]
        if user is not None:
            campo_relacionado(self, "cliente").queryset = queryset_da_empresa(
                Cliente.objects.all(), user
            )
            self.fields["cliente"].required = False
            campo_relacionado(self, "projeto").queryset = queryset_da_empresa(
                Projeto.objects.all(), user
            )
            self.fields["projeto"].required = False
