from django import forms

from core.tenancy import queryset_da_empresa
from crm.models import Cliente
from projetos.models import Projeto

from .models import ItemProposta, Proposta
from core.forms import ArqModelForm

class PropostaForm(ArqModelForm):
    tipo_projeto = forms.ChoiceField(choices=Projeto.TIPO_CHOICES)

    class Meta:
        model = Proposta
        fields = ["titulo", "cliente", "tipo_projeto", "validade", "observacoes"]
        widgets = {
            "validade": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, projeto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["cliente"].queryset = queryset_da_empresa(Cliente.objects.all(), user)
        if self.instance and self.instance.pk and self.instance.projeto_gerado_id:
            self.fields["cliente"].disabled = True
            self.fields["tipo_projeto"].disabled = True
        if projeto is not None:
            # Vindo de um projeto, cliente e tipo já estão decididos: não faz
            # sentido perguntar de novo, e errar aqui desliga a proposta do
            # projeto sem ninguém perceber.
            self.fields["cliente"].initial = projeto.cliente_id
            self.fields["cliente"].disabled = True
            self.fields["tipo_projeto"].initial = projeto.tipo
            self.fields["titulo"].initial = f"Proposta — {projeto.nome}"


class ItemPropostaForm(ArqModelForm):
    """Uma linha só, no rodapé da tabela — daí o rótulo virar placeholder.

    Sem ele os dois campos ficam sem contorno e sem nome, e a linha lê como
    duas lacunas soltas com um zero no meio.
    """

    class Meta:
        model = ItemProposta
        fields = ["descricao", "inclusoes", "horas_estimadas"]
        widgets = {
            "descricao": forms.TextInput(attrs={"placeholder": "Etapa ou serviço"}),
            "inclusoes": forms.Textarea(attrs={"placeholder": "O que está incluído", "rows": 2}),
            "horas_estimadas": forms.NumberInput(attrs={"placeholder": "Horas", "step": "0.5"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Integrações e propostas antigas que enviavam só o título continuam
        # válidas; o item nunca fica sem explicação, pois recebe este texto.
        self.fields["inclusoes"].required = False
        # O default 0 do modelo virava valor inicial e escondia o placeholder:
        # o campo mostrava um zero solto no lugar de dizer o que se escreve ali.
        self.fields["horas_estimadas"].initial = None

    def clean_inclusoes(self):
        return self.cleaned_data.get("inclusoes", "").strip() or (
            "Entregáveis e atividades conforme o escopo desta etapa."
        )
