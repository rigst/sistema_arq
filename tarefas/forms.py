from django import forms

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .models import Tarefa
from core.forms import ArqModelForm


class TarefaForm(ArqModelForm):
    class Meta:
        model = Tarefa
        fields = ["titulo", "descricao", "projeto", "responsavel", "criterio_pronto", "prazo", "status"]
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
