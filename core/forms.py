from django import forms


class SemDoisPontosMixin:
    """Tira o ':' que o Django acrescenta a todo rótulo.

    Os rótulos do A.R.Q. são impressos em monoespaçada e caixa alta, como
    numa folha de especificação — ali o dois-pontos vira sujeira.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class ArqModelForm(SemDoisPontosMixin, forms.ModelForm):
    pass


class ArqForm(SemDoisPontosMixin, forms.Form):
    pass
