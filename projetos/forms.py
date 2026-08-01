from django import forms

from crm.models import Cliente
from core.tenancy import queryset_da_empresa

from .models import Disciplina, Etapa, Pendencia, Projeto
from core.forms import ArqModelForm


class ProjetoForm(ArqModelForm):
    """Status só aparece quando já existe um projeto para mudar de estado.

    Perguntar "qual o status?" na criação é perguntar o óbvio: quem está
    cadastrando um projeto está cadastrando um projeto ativo.
    """

    class Meta:
        model = Projeto
        fields = [
            "nome", "cliente", "tipo", "tem_execucao", "status",
            "valor_contratado", "data_inicio", "data_prevista", "tags",
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


class PendenciaForm(ArqModelForm):
    class Meta:
        model = Pendencia
        fields = ["descricao", "prazo"]
        widgets = {"prazo": forms.DateInput(attrs={"type": "date"})}


class DisciplinaForm(ArqModelForm):
    """Uma disciplina do projeto — arquitetônico, estrutural, hidráulico.

    Quem executa é a pergunta que importa: interna (o escritório) ou de um
    projetista externo já cadastrado em fornecedores.
    """

    class Meta:
        model = Disciplina
        fields = ["nome", "descricao", "interna", "fornecedor", "prazo"]
        widgets = {"prazo": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from fornecedores.models import Fornecedor

        self.fields["fornecedor"].queryset = queryset_da_empresa(
            Fornecedor.objects.filter(ativo=True), user
        )
        self.fields["fornecedor"].empty_label = "— sem projetista externo —"

    def clean(self):
        dados = super().clean()
        if not dados.get("interna") and not dados.get("fornecedor"):
            self.add_error(
                "fornecedor",
                "Disciplina externa precisa de um projetista. "
                "Cadastre-o em Fornecedores, ou marque como feita pelo escritório.",
            )
        return dados


class EtapaFornecedorForm(ArqModelForm):
    """Quem executa uma etapa, quando ela é terceirizada."""

    class Meta:
        model = Etapa
        fields = ["fornecedor"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from fornecedores.models import Fornecedor

        self.fields["fornecedor"].queryset = queryset_da_empresa(
            Fornecedor.objects.filter(ativo=True), user
        )
        self.fields["fornecedor"].empty_label = "— equipe interna —"
