from django.contrib import admin

from .models import Compromisso


@admin.register(Compromisso)
class CompromissoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "inicio", "cliente", "projeto")
    list_filter = ("tipo",)
    search_fields = ("titulo",)
