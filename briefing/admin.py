from django.contrib import admin

from .models import (
    AmbientePrograma,
    Briefing,
    OpcaoPergunta,
    PerguntaTemplate,
    RespostaBriefing,
    TemplateBriefing,
)


class AmbienteInline(admin.TabularInline):
    model = AmbientePrograma
    extra = 0


@admin.register(Briefing)
class BriefingAdmin(admin.ModelAdmin):
    list_display = ("projeto", "orcamento_previsto", "prazo_desejado", "atualizado_em")
    inlines = [AmbienteInline]


class PerguntaInline(admin.TabularInline):
    model = PerguntaTemplate
    extra = 0


@admin.register(TemplateBriefing)
class TemplateBriefingAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo_projeto", "ativo", "empresa", "atualizado_em")
    list_filter = ("tipo_projeto", "ativo")
    search_fields = ("nome", "descricao")
    inlines = [PerguntaInline]


admin.site.register(AmbientePrograma)
admin.site.register(PerguntaTemplate)
admin.site.register(OpcaoPergunta)
admin.site.register(RespostaBriefing)
