from django import forms


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            rotulo = campo.label
            if not rotulo or "aria-label" in campo.widget.attrs:
                continue
            if isinstance(campo.widget, (forms.CheckboxInput, forms.RadioSelect,
                                         forms.CheckboxSelectMultiple)):
                # Marcações vêm sempre com rótulo visível ao lado; repetir aqui
                # faria o leitor de tela anunciar o texto duas vezes.
                continue
            campo.widget.attrs["aria-label"] = str(rotulo)


class ArqModelForm(NomeAcessivelMixin, SemDoisPontosMixin, forms.ModelForm):
    pass


class ArqForm(NomeAcessivelMixin, SemDoisPontosMixin, forms.Form):
    pass
