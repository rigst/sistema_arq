from decimal import Decimal

from django import forms

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .models import ApontamentoHora, Tarefa
from core.forms import ArqModelForm


class ApontamentoForm(forms.Form):
    """Lançamento à mão: o que foi feito e quanto tempo levou.

    Nem toda hora passa pelo cronômetro — quem lembra do trabalho de ontem
    à noite precisa poder escrever, senão a conta do projeto fica pela metade
    e a margem mente.
    """

    descricao = forms.CharField(
        label="Descrição", max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "O que foi feito"}),
    )
    horas = forms.DecimalField(
        label="Horas", max_digits=8, decimal_places=2, min_value=Decimal("0.01"),
        widget=forms.NumberInput(attrs={"placeholder": "0,00", "step": "any", "min": "0.01"}),
    )


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
