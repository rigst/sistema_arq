from django.contrib import admin

from .models import AlteracaoEscopo, Contrato, Documento, Parcela


class ParcelaInline(admin.TabularInline):
    model = Parcela
    extra = 0


class AlteracaoInline(admin.TabularInline):
    model = AlteracaoEscopo
    extra = 0


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "projeto", "valor_total", "status", "data_assinatura")
    list_filter = ("status",)
    search_fields = ("titulo", "numero")
    inlines = [ParcelaInline, AlteracaoInline]


admin.site.register(Parcela)
admin.site.register(AlteracaoEscopo)
admin.site.register(Documento)
