from django import forms

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .models import ObrigacaoTecnica
from core.forms import ArqModelForm


class ObrigacaoTecnicaForm(ArqModelForm):
    class Meta:
        model = ObrigacaoTecnica
        fields = [
            "tipo", "projeto", "numero", "responsavel_tecnico", "status",
            "data_registro", "vencimento", "valor", "arquivo", "observacoes",
        ]
        labels = {
            "responsavel_tecnico": "Responsável técnico",
            "data_registro": "Data de registro",
            "observacoes": "Observações",
        }
        widgets = {
            "data_registro": forms.DateInput(attrs={"type": "date"}),
            "vencimento": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["projeto"].queryset = queryset_da_empresa(Projeto.objects.all(), user)
        self.fields["projeto"].required = False
