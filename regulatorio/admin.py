from django.contrib import admin

from .models import ObrigacaoTecnica


@admin.register(ObrigacaoTecnica)
class ObrigacaoTecnicaAdmin(admin.ModelAdmin):
    list_display = ("tipo", "numero", "projeto", "status", "vencimento")
    list_filter = ("tipo", "status")
    search_fields = ("numero", "responsavel_tecnico")
