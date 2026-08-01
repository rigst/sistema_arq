from django.contrib import admin

from .models import Pendencia, Projeto, Tag


class PendenciaInline(admin.TabularInline):
    model = Pendencia
    extra = 0


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "tipo", "status", "valor_contratado", "ultima_atualizacao")
    list_filter = ("tipo", "status")
    search_fields = ("nome",)
    inlines = [PendenciaInline]


admin.site.register(Tag)
