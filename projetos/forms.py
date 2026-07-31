from django import forms

from crm.models import Cliente
from core.tenancy import queryset_da_empresa

from .models import Pendencia, Projeto


class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = ["nome", "cliente", "tipo", "status", "valor_contratado", "data_inicio", "data_prevista", "tags"]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_prevista": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["cliente"].queryset = queryset_da_empresa(
                Cliente.objects.filter(ativo=True), user
            )
            from .models import Tag

            self.fields["tags"].queryset = queryset_da_empresa(Tag.objects.all(), user)


class PendenciaForm(forms.ModelForm):
    class Meta:
        model = Pendencia
        fields = ["descricao", "prazo"]
        widgets = {"prazo": forms.DateInput(attrs={"type": "date"})}
