from django import forms
from django.db.models import Q

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .models import EtapaObra, Medicao, Obra, VisitaTecnica
from core.forms import ArqModelForm


class ObraForm(ArqModelForm):
    class Meta:
        model = Obra
        fields = [
            "projeto", "endereco", "responsavel_tecnico", "status",
            "data_inicio", "data_prevista_fim", "observacoes",
        ]
        labels = {
            "responsavel_tecnico": "Responsável técnico",
            "data_prevista_fim": "Previsão de término",
            "observacoes": "Observações",
        }
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_prevista_fim": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            # Só projetos sem obra (na edição, mantém o projeto já vinculado).
            qs = queryset_da_empresa(Projeto.objects.all(), user)
            if self.instance.pk:
                qs = qs.filter(Q(obra__isnull=True) | Q(pk=self.instance.projeto_id))
            else:
                qs = qs.filter(obra__isnull=True)
            self.fields["projeto"].queryset = qs


class EtapaObraForm(ArqModelForm):
    class Meta:
        model = EtapaObra
        fields = [
            "nome", "ordem", "data_prevista_inicio", "data_prevista_fim",
            "percentual_previsto", "percentual_real", "valor",
        ]
        widgets = {
            "data_prevista_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_prevista_fim": forms.DateInput(attrs={"type": "date"}),
        }


class VisitaTecnicaForm(ArqModelForm):
    class Meta:
        model = VisitaTecnica
        fields = ["etapa", "data", "verificado", "pendencias", "proxima_acao"]
        labels = {
            "proxima_acao": "Próxima ação",
            "pendencias": "Pendências",
        }
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "verificado": forms.Textarea(attrs={"rows": 2}),
            "pendencias": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, obra=None, **kwargs):
        super().__init__(*args, **kwargs)
        if obra is not None:
            self.fields["etapa"].queryset = obra.etapas.all()
            self.fields["etapa"].required = False


class MedicaoForm(ArqModelForm):
    class Meta:
        model = Medicao
        fields = ["etapa", "data", "percentual_medido", "valor_liberado", "descricao"]
        labels = {"descricao": "Descrição"}
        widgets = {"data": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, obra=None, **kwargs):
        super().__init__(*args, **kwargs)
        if obra is not None:
            self.fields["etapa"].queryset = obra.etapas.all()
