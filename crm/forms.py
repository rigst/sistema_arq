from django import forms

from .models import Cliente, Interacao
from core.forms import ArqModelForm


class ClienteForm(ArqModelForm):
    class Meta:
        model = Cliente
        fields = ["nome", "email", "telefone", "origem", "fase", "observacoes", "ativo"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}


class InteracaoForm(ArqModelForm):
    class Meta:
        model = Interacao
        fields = ["tipo", "descricao"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 2})}
