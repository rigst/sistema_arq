from django.contrib import admin

from .models import Arquivo


@admin.register(Arquivo)
class ArquivoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "projeto", "fluxo", "categoria", "status", "valor", "criado_em")
    list_filter = ("fluxo", "categoria", "status")
    search_fields = ("titulo", "observacoes")
