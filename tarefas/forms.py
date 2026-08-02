from django import forms

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .models import Tarefa
from core.forms import ArqModelForm


class TarefaForm(ArqModelForm):
    class Meta:
        model = Tarefa
        fields = [
            "titulo", "descricao", "projeto", "fase", "responsavel", "fornecedor",
            "criterio_pronto", "prazo", "status",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
            "prazo": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, projeto=None, **kwargs):
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

        if projeto is not None:
            # Dentro de um projeto, ele já está decidido — e as fases oferecidas
            # são as dele, não as de todos os projetos da empresa.
            self.fields["projeto"].initial = projeto.pk
            self.fields["projeto"].disabled = True
            self.fields["fase"].queryset = projeto.fases.all()
            self.fields["fase"].empty_label = "— sem fase específica —"
        elif user is not None:
            from fases.models import Fase

            self.fields["fase"].queryset = queryset_da_empresa(
                Fase.objects.select_related("projeto"), user
            )
            self.fields["fase"].empty_label = "— sem fase específica —"
        self.fields["fase"].required = False

        # Tarefa nova nasce aberta; status é acompanhamento, não cadastro.
        if self.instance.pk is None and "status" in self.fields:
            del self.fields["status"]
