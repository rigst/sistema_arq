from django import forms

from .models import Cliente, Interacao


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nome", "email", "telefone", "origem", "fase", "observacoes", "ativo"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}


class InteracaoForm(forms.ModelForm):
    class Meta:
        model = Interacao
        fields = ["tipo", "descricao"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 2})}
