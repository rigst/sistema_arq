from django import forms

from core.forms import ArqModelForm
from core.tenancy import queryset_da_empresa
from fornecedores.models import Fornecedor
from projetos.models import Projeto

from .models import Arquivo


class ArquivoForm(ArqModelForm):
    class Meta:
        model = Arquivo
        fields = [
            "titulo",
            "arquivo",
            "projeto",
            "fluxo",
            "categoria",
            "status",
            "data",
            "valor",
            "fornecedor",
            "observacoes",
        ]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["projeto"].queryset = queryset_da_empresa(Projeto.objects.all(), user)
            self.fields["fornecedor"].queryset = queryset_da_empresa(
                Fornecedor.objects.filter(ativo=True), user
            )
        else:
            self.fields["projeto"].queryset = Projeto.objects.none()
            self.fields["fornecedor"].queryset = Fornecedor.objects.none()
        self.fields["projeto"].empty_label = "Sem projeto (escritório)"
        self.fields["fornecedor"].empty_label = "Sem fornecedor"
