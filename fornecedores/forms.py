from django import forms

from core.forms import ArqModelForm

from .models import Fornecedor


class FornecedorForm(ArqModelForm):
    class Meta:
        model = Fornecedor
        fields = [
            "nome",
            "categoria",
            "contato",
            "telefone",
            "email",
            "site",
            "documento",
            "cidade",
            "prazo_medio_dias",
            "avaliacao",
            "ativo",
            "observacoes",
        ]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            del self.fields["ativo"]
