from django import forms

from core.forms import ArqForm, ArqModelForm
from core.tenancy import queryset_da_empresa
from tarefas.models import Tarefa

from .models import Fase, Lembrete


class FaseAjusteForm(ArqModelForm):
    """Prazo e responsável da fase. O status não entra: quem muda estado são os
    botões do fluxo, que registram data e autor junto."""

    class Meta:
        model = Fase
        fields = ["prazo", "fornecedor"]
        widgets = {"prazo": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from fornecedores.models import Fornecedor

        self.fields["fornecedor"].queryset = queryset_da_empresa(
            Fornecedor.objects.filter(ativo=True), user
        )
        self.fields["fornecedor"].empty_label = "— equipe do escritório —"


class LembreteForm(ArqModelForm):
    """Só o texto. Pedir o tipo era uma pergunta a mais para escrever um
    recado de duas linhas, e a resposta não mudava nada no sistema."""

    class Meta:
        model = Lembrete
        fields = ["texto"]
        widgets = {
            "texto": forms.Textarea(
                attrs={"rows": 4, "placeholder": "O que foi combinado, decidido ou pedido."}
            )
        }
        labels = {"texto": "Lembrete"}


class RespostaClienteForm(ArqForm):
    parecer = forms.CharField(
        label="O que o cliente disse",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Fica no histórico da fase e explica a decisão para quem vier depois.",
    )


class FaseTarefaForm(ArqModelForm):
    class Meta:
        model = Tarefa
        fields = ["titulo", "prazo", "horas_previstas"]
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Nova tarefa ou entregável"}),
            "prazo": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "horas_previstas": forms.NumberInput(
                attrs={"step": "0.5", "min": "0", "placeholder": "0"}
            ),
        }

    def __init__(self, *args, form_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if form_id:
            for field in self.fields.values():
                field.widget.attrs["form"] = form_id


class ArquivoDaFaseForm(ArqModelForm):
    """Upload dentro da fase: sem perguntar projeto nem fase, que já se sabe."""

    class Meta:
        from arquivos.models import Arquivo

        model = Arquivo
        fields = ["titulo", "arquivo", "categoria", "fluxo", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 2})}
        labels = {"titulo": "Nome do arquivo"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["observacoes"].required = False


class RenomearArquivoForm(ArqModelForm):
    class Meta:
        from arquivos.models import Arquivo

        model = Arquivo
        fields = ["titulo", "categoria", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 2})}
        labels = {"titulo": "Nome do arquivo"}
