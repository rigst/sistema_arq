from django import forms

from core.forms import ArqModelForm, campo_relacionado
from core.tenancy import queryset_da_empresa
from fornecedores.models import Fornecedor

from .models import ItemOrcamento, Orcamento


class OrcamentoForm(ArqModelForm):
    class Meta:
        model = Orcamento
        fields = ["titulo", "versao", "status", "bdi_percent", "validade", "observacoes"]
        widgets = {
            "validade": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class ItemOrcamentoForm(ArqModelForm):
    class Meta:
        model = ItemOrcamento
        fields = [
            "ambiente",
            "categoria",
            "descricao",
            "unidade",
            "quantidade",
            "valor_unitario",
            "fornecedor",
            "observacoes",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # O select de fornecedor só pode oferecer fornecedores da própria empresa.
        base = Fornecedor.objects.filter(ativo=True)
        campo_relacionado(self, "fornecedor").queryset = (
            queryset_da_empresa(base, user) if user else Fornecedor.objects.none()
        )
        campo_relacionado(self, "fornecedor").empty_label = "Sem fornecedor definido"
