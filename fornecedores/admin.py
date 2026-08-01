from django.contrib import admin

from .models import Fornecedor


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "cidade", "avaliacao", "ativo")
    list_filter = ("categoria", "ativo")
    search_fields = ("nome", "contato", "email", "cidade")
