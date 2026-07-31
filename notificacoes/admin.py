from django.contrib import admin

from .models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "nivel", "lida", "criado_em")
    list_filter = ("nivel", "lida")
