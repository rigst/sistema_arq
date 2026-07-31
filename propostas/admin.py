from django.contrib import admin

from .models import ItemProposta, Proposta


class ItemInline(admin.TabularInline):
    model = ItemProposta
    extra = 0


@admin.register(Proposta)
class PropostaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "cliente", "status", "hora_tecnica_aplicada", "criado_em")
    list_filter = ("status",)
    search_fields = ("titulo",)
    inlines = [ItemInline]
