from django.contrib import admin

from .models import AvisoSistema, Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "nivel", "lida", "criado_em")
    list_filter = ("nivel", "lida")


@admin.register(AvisoSistema)
class AvisoSistemaAdmin(admin.ModelAdmin):
    list_display = ("texto", "nivel", "onde", "usuario", "criado_em", "empresa")
    list_filter = ("nivel", "criado_em")
    search_fields = ("texto", "onde", "usuario__username")
