from django import forms

from .models import AmbientePrograma, Briefing, TemplateBriefing
from core.forms import ArqModelForm


class BriefingForm(ArqModelForm):
    """Os blocos da NBR. Os campos declaram `form="briefing"` para poderem
    ficar fora da tag <form> no HTML e ainda assim serem enviados por ela —
    é o que permite um botão de salvar só, com o programa de necessidades
    (que tem formulário próprio) no meio da página."""

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["form"] = "briefing"


class AmbienteForm(ArqModelForm):
    class Meta:
        model = AmbientePrograma
        fields = ["nome", "area_aprox", "uso"]


class TemplateBriefingForm(ArqModelForm):
    class Meta:
        model = TemplateBriefing
        fields = ["nome", "tipo_projeto", "descricao", "ativo"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            del self.fields["ativo"]
