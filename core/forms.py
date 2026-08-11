from typing import TYPE_CHECKING, cast

from django import forms


def campo_relacionado(formulario: forms.BaseForm, nome: str) -> forms.ModelChoiceField:
    """O campo de escolha por relação, para ajustar `queryset` e `empty_label`.

    `formulario.fields` é `dict[str, Field]`, e esses dois atributos só existem
    em `ModelChoiceField`. O formulário sabe qual campo é qual; o verificador de
    tipos, não. Esta função é onde essa afirmação fica escrita uma vez, em vez
    de repetida em cada `__init__` que restringe um select por empresa.
    """
    return cast(forms.ModelChoiceField, formulario.fields[nome])


class SemDoisPontosMixin:
    """Tira o ':' que o Django acrescenta a todo rótulo.

    Os rótulos do A.R.Q. são impressos em monoespaçada e caixa alta, como
    numa folha de especificação — ali o dois-pontos vira sujeira.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class NomeAcessivelMixin:
    """Todo campo carrega o próprio rótulo em aria-label.

    Vários formulários do sistema aparecem em linha — adicionar pendência,
    lançar custo, gerar parcelas — e ali o rótulo visível seria ruído: a coluna
    já diz o que é. Só que sem rótulo o campo fica mudo para quem usa leitor de
    tela. Escrever isso à mão em cada template é o tipo de coisa que se esquece
    no template seguinte, então nasce com o formulário.

    Onde o rótulo visível existe, o `for`/`id` continua valendo e o aria-label
    apenas repete o mesmo texto, sem conflito.
    """

    if TYPE_CHECKING:
        # Quem traz `fields` é o Form ao lado do qual este mixin sempre entra.
        # Declarar aqui deixa o corpo do __init__ ser verificado sem herdar de
        # Form — herança que criaria MRO errado e mudaria o comportamento.
        fields: dict[str, forms.Field]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            if isinstance(campo, forms.DecimalField) and (
                nome == "valor"
                or nome.startswith("valor_")
                or nome in {"saldo_inicial", "orcamento_previsto", "hora_tecnica_manual"}
            ):
                attrs = {
                    chave: valor
                    for chave, valor in campo.widget.attrs.items()
                    if chave not in {"min", "max", "step"}
                }
                attrs.update({"inputmode": "decimal", "data-moeda-br": ""})
                campo.widget = forms.TextInput(attrs=attrs)
            rotulo = campo.label
            if not rotulo or "aria-label" in campo.widget.attrs:
                continue
            if isinstance(
                campo.widget, (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)
            ):
                # Marcações vêm sempre com rótulo visível ao lado; repetir aqui
                # faria o leitor de tela anunciar o texto duas vezes.
                continue
            campo.widget.attrs["aria-label"] = str(rotulo)


class ArqModelForm(NomeAcessivelMixin, SemDoisPontosMixin, forms.ModelForm):
    pass


class ArqForm(NomeAcessivelMixin, SemDoisPontosMixin, forms.Form):
    pass
