from django import forms

from core.forms import ArqForm, ArqModelForm, campo_relacionado
from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .models import AlteracaoEscopo, Contrato, Documento, ModeloContrato, Parcela


class ContratoForm(ArqModelForm):
    class Meta:
        model = Contrato
        fields = ["projeto", "titulo", "numero", "valor_total", "corpo", "observacoes"]
        widgets = {
            "corpo": forms.Textarea(
                attrs={"rows": 24, "class": "contrato-corpo", "spellcheck": "true"}
            ),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, projeto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            campo_relacionado(self, "projeto").queryset = queryset_da_empresa(
                Projeto.objects.all(), user
            )
        if self.instance and self.instance.pk:
            # Um contrato não troca de projeto durante a revisão da minuta.
            self.fields["projeto"].disabled = True
        if projeto is not None:
            self.fields["projeto"].initial = projeto.pk
            self.fields["projeto"].disabled = True
            self.fields["titulo"].initial = f"Contrato — {projeto.nome}"
            if projeto.valor_contratado:
                self.fields["valor_total"].initial = projeto.valor_contratado


class GerarParcelasForm(ArqForm):
    quantidade = forms.IntegerField(min_value=1, max_value=60, initial=1, label="Nº de parcelas")
    primeira_data = forms.DateField(
        label="1º vencimento", widget=forms.DateInput(attrs={"type": "date"})
    )


class AssinaturaContratoForm(ArqForm):
    data_assinatura = forms.DateField(
        label="Data da assinatura", widget=forms.DateInput(attrs={"type": "date"})
    )


class ParcelaForm(ArqModelForm):
    class Meta:
        model = Parcela
        fields = ["descricao", "valor", "vencimento"]
        widgets = {
            "descricao": forms.TextInput(attrs={"placeholder": "Descrição da parcela"}),
            "valor": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0,00"}),
            "vencimento": forms.DateInput(attrs={"type": "date"}),
        }


class AlteracaoEscopoForm(ArqModelForm):
    class Meta:
        model = AlteracaoEscopo
        fields = ["tipo", "descricao", "valor_delta"]
        widgets = {
            "descricao": forms.Textarea(
                attrs={"rows": 1, "placeholder": "Descreva o que mudou e o que foi acordado"}
            ),
            "valor_delta": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0,00"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["valor_delta"].label = "Impacto financeiro"
        self.fields[
            "valor_delta"
        ].help_text = "Use 0,00 quando não houver impacto; valor positivo aumenta e negativo reduz."


class DocumentoForm(ArqModelForm):
    class Meta:
        model = Documento
        fields = ["titulo", "arquivo"]
        widgets = {"titulo": forms.TextInput(attrs={"placeholder": "Ex.: Aditivo assinado"})}


class DocumentoEdicaoForm(ArqModelForm):
    arquivo = forms.FileField(required=False, label="Substituir arquivo")

    class Meta:
        model = Documento
        fields = ["titulo", "arquivo"]


class ModeloContratoForm(ArqModelForm):
    tipo_projeto = forms.ChoiceField(
        choices=[("", "Qualquer tipo"), *Projeto.TIPO_CHOICES], required=False
    )

    class Meta:
        model = ModeloContrato
        fields = ["nome", "tipo_projeto", "descricao", "corpo", "padrao", "ativo"]
        widgets = {"corpo": forms.Textarea(attrs={"rows": 20, "spellcheck": "true"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            del self.fields["ativo"]
