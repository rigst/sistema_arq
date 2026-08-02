from django import forms

from crm.models import Cliente
from core.tenancy import queryset_da_empresa

from .models import Projeto
from core.forms import ArqModelForm


class ProjetoForm(ArqModelForm):
    """Status só aparece quando já existe um projeto para mudar de estado.

    Perguntar "qual o status?" na criação é perguntar o óbvio: quem está
    cadastrando um projeto está cadastrando um projeto ativo.
    """

    class Meta:
        model = Projeto
        fields = [
            "nome", "cliente", "tipo", "status",
            "endereco", "cidade", "uf", "cep", "area_terreno", "area_construida",
            "valor_contratado", "data_inicio", "data_prevista", "tem_execucao", "tags",
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
            self.fields["cliente"].queryset = queryset_da_empresa(
                Cliente.objects.filter(ativo=True), user
            )
            from .models import Tag

            self.fields["tags"].queryset = queryset_da_empresa(Tag.objects.all(), user)
