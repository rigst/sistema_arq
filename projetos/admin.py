from django.contrib import admin

from .models import Projeto, Tag


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "tipo", "status", "valor_contratado", "ultima_atualizacao")
    list_filter = ("tipo", "status")
    search_fields = ("nome",)


admin.site.register(Tag)
