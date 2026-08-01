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
