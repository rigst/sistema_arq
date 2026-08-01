from django import forms

from .models import AmbientePrograma, Briefing, TemplateBriefing
from core.forms import ArqModelForm


class BriefingForm(ArqModelForm):
    class Meta:
        model = Briefing
        fields = [
            "perfil_usuarios",
            "orcamento_previsto",
            "prazo_desejado",
            "restricoes",
            "referencias",
            "estilo",
        ]
        widgets = {
            "perfil_usuarios": forms.Textarea(attrs={"rows": 3}),
            "restricoes": forms.Textarea(attrs={"rows": 3}),
            "referencias": forms.Textarea(attrs={"rows": 3}),
            "prazo_desejado": forms.DateInput(attrs={"type": "date"}),
        }


class AmbienteForm(ArqModelForm):
    class Meta:
        model = AmbientePrograma
        fields = ["nome", "area_aprox", "uso"]


class TemplateBriefingForm(ArqModelForm):
    class Meta:
        model = TemplateBriefing
        fields = ["nome", "tipo_projeto", "descricao", "ativo"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 2})}
