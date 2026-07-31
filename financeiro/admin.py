from django.contrib import admin

from .models import Categoria, ContaBancaria, Lancamento


@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ("data", "tipo", "descricao", "valor", "status", "conta", "projeto")
    list_filter = ("tipo", "status")
    search_fields = ("descricao",)


admin.site.register(ContaBancaria)
admin.site.register(Categoria)
