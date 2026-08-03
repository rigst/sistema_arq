from django.contrib import admin

from .models import ItemOrcamento, Orcamento


class ItemInline(admin.TabularInline):
    model = ItemOrcamento
    extra = 0


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "projeto", "versao", "status", "criado_em")
    list_filter = ("status",)
    inlines = [ItemInline]


@admin.register(ItemOrcamento)
class ItemOrcamentoAdmin(admin.ModelAdmin):
    list_display = ("descricao", "orcamento", "quantidade", "valor_unitario", "categoria")
    list_filter = ("categoria",)
    search_fields = ("descricao", "orcamento__titulo")
