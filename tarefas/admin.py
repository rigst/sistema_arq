from django.contrib import admin

from .models import ApontamentoHora, Tarefa


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "projeto", "responsavel", "prazo", "status")
    list_filter = ("status",)
    search_fields = ("titulo",)


@admin.register(ApontamentoHora)
class ApontamentoHoraAdmin(admin.ModelAdmin):
    list_display = ("usuario", "projeto", "tarefa", "inicio", "fim")
    list_filter = ("usuario",)
