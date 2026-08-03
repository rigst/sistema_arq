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
    filter_horizontal = ("fatores",)


@admin.register(ItemProposta)
class ItemPropostaAdmin(admin.ModelAdmin):
    list_display = ("descricao", "proposta", "horas_estimadas", "valor", "ordem")
    search_fields = ("descricao", "proposta__titulo")
