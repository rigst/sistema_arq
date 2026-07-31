from django.contrib import admin

from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nome", "grupo", "ativa", "criada_em")
    list_filter = ("ativa",)
    search_fields = ("nome",)
    readonly_fields = ("criada_em", "atualizada_em")
