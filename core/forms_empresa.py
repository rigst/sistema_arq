"""Identidade visual do escritório.

Fica separado de core/forms.py porque aquele arquivo guarda as bases (ArqForm,
ArqModelForm) das quais todo formulário do sistema herda, e misturar um
formulário concreto ali embaralharia as duas coisas.
"""

from django import forms

from core.forms import ArqModelForm
from core.models import Empresa


class IdentidadeEmpresaForm(ArqModelForm):
    """Logo e imagem de fundo do painel.

    São os dois lugares onde o escritório se reconhece no sistema: a marca na
    barra lateral e a foto que abre o painel — de preferência uma obra da casa.
    """

    limpar_logo = forms.BooleanField(label="Remover a logo atual", required=False)
    limpar_fundo = forms.BooleanField(label="Remover a imagem de fundo atual", required=False)

    class Meta:
        model = Empresa
        fields = ["nome", "logo", "imagem_fundo", "cor_primaria"]
        widgets = {"cor_primaria": forms.TextInput(attrs={"type": "color"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].help_text = (
            "PNG ou SVG com fundo transparente. Aparece na barra lateral e nos documentos."
        )
        self.fields["cor_primaria"].required = False

    def save(self, commit=True):
        empresa = super().save(commit=False)
        # O checkbox de limpar vem depois do upload de propósito: se a pessoa
        # mandou arquivo novo e marcou limpar, o arquivo novo ganha.
        if self.cleaned_data.get("limpar_logo") and not self.files.get("logo"):
            empresa.logo = None
        if self.cleaned_data.get("limpar_fundo") and not self.files.get("imagem_fundo"):
            empresa.imagem_fundo = None
        if commit:
            empresa.save()
        return empresa
