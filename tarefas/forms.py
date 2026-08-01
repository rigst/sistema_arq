from django import forms

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .models import Tarefa
from core.forms import ArqModelForm


class TarefaForm(ArqModelForm):
    class Meta:
        model = Tarefa
        fields = [
            "titulo", "descricao", "projeto", "responsavel", "fornecedor",
            "criterio_pronto", "prazo", "status",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
            "prazo": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["projeto"].queryset = queryset_da_empresa(Projeto.objects.all(), user)
            self.fields["projeto"].required = False

            from core.tenancy import obter_grupo_empresa_usuario

            grupo = obter_grupo_empresa_usuario(user)
            if grupo is not None:
                self.fields["responsavel"].queryset = grupo.user_set.all()
            self.fields["responsavel"].required = False

            # Nem toda tarefa é da equipe: detalhamento de marcenaria, cálculo
            # estrutural e afins saem para quem executa.
            from fornecedores.models import Fornecedor

            self.fields["fornecedor"].queryset = queryset_da_empresa(
                Fornecedor.objects.filter(ativo=True), user
            )
            self.fields["fornecedor"].empty_label = "— equipe interna —"
            self.fields["fornecedor"].required = False

        # Tarefa nova nasce aberta; status é acompanhamento, não cadastro.
        if self.instance.pk is None and "status" in self.fields:
            del self.fields["status"]
