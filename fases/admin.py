from django.contrib import admin

from .models import Fase, Lembrete


@admin.register(Fase)
class FaseAdmin(admin.ModelAdmin):
    list_display = ("nome", "projeto", "ordem", "status", "prazo", "complementar", "empresa")
    list_filter = ("status", "chave")
    search_fields = ("nome", "projeto__nome", "resumo")


@admin.register(Lembrete)
class LembreteAdmin(admin.ModelAdmin):
    list_display = ("texto", "projeto", "fase", "autor", "criado_em", "empresa")
    list_filter = ("criado_em",)
    search_fields = ("texto", "projeto__nome")
