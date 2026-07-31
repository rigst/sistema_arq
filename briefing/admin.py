from django.contrib import admin

from .models import AmbientePrograma, Briefing


class AmbienteInline(admin.TabularInline):
    model = AmbientePrograma
    extra = 0


@admin.register(Briefing)
class BriefingAdmin(admin.ModelAdmin):
    list_display = ("projeto", "orcamento_previsto", "prazo_desejado", "atualizado_em")
    inlines = [AmbienteInline]
