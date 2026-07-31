from django.contrib import admin

from .models import EtapaObra, Medicao, Obra, VisitaTecnica


class EtapaObraInline(admin.TabularInline):
    model = EtapaObra
    extra = 0


class VisitaInline(admin.TabularInline):
    model = VisitaTecnica
    extra = 0


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("projeto", "status", "data_inicio", "data_prevista_fim")
    list_filter = ("status",)
    inlines = [EtapaObraInline, VisitaInline]


@admin.register(EtapaObra)
class EtapaObraAdmin(admin.ModelAdmin):
    list_display = ("nome", "obra", "percentual_previsto", "percentual_real", "valor")


admin.site.register(VisitaTecnica)
admin.site.register(Medicao)
