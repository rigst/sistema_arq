from django import forms

from core.forms import ArqModelForm

from .models import Cliente, Interacao


class ClienteForm(ArqModelForm):
    """Fase e "ativo" não se perguntam na criação: cliente novo nasce ativo, no
    começo do funil. São campos de acompanhamento, não de cadastro."""

    class Meta:
        model = Cliente
        fields = ["nome", "email", "telefone", "origem", "fase", "observacoes", "ativo"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            del self.fields["fase"]
            del self.fields["ativo"]


class InteracaoForm(ArqModelForm):
    class Meta:
        model = Interacao
        fields = ["tipo", "descricao"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 2})}
