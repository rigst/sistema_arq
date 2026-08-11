from django import forms

from core.forms import ArqModelForm, campo_relacionado
from core.tenancy import queryset_da_empresa
from crm.models import Cliente

from .models import Projeto


class ProjetoForm(ArqModelForm):
    """Status só aparece quando já existe um projeto para mudar de estado.

    Perguntar "qual o status?" na criação é perguntar o óbvio: quem está
    cadastrando um projeto está cadastrando um projeto ativo.
    """

    class Meta:
        model = Projeto
        fields = [
            "nome",
            "cliente",
            "tipo",
            "status",
            "endereco",
            "cidade",
            "uf",
            "cep",
            "area_terreno",
            "area_construida",
            "valor_contratado",
            "data_inicio",
            "data_prevista",
            "tem_execucao",
            "tags",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_prevista": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            del self.fields["status"]
        if user is not None:
            campo_relacionado(self, "cliente").queryset = queryset_da_empresa(
                Cliente.objects.filter(ativo=True), user
            )
            from .models import Tag

            campo_relacionado(self, "tags").queryset = queryset_da_empresa(Tag.objects.all(), user)


class PlanejamentoProjetoForm(ArqModelForm):
    """Dados internos de planejamento, separados do que vai na proposta."""

    class Meta:
        model = Projeto
        fields = ["horas_estimadas", "data_inicio", "data_prevista"]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_prevista": forms.DateInput(attrs={"type": "date"}),
            "horas_estimadas": forms.NumberInput(attrs={"step": "0.5", "min": "0"}),
        }
