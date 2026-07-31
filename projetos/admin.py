from django.contrib import admin

from .models import Etapa, Pendencia, Projeto, Tag


class EtapaInline(admin.TabularInline):
    model = Etapa
    extra = 0


class PendenciaInline(admin.TabularInline):
    model = Pendencia
    extra = 0


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "tipo", "status", "valor_contratado", "ultima_atualizacao")
    list_filter = ("tipo", "status")
    search_fields = ("nome",)
    inlines = [EtapaInline, PendenciaInline]


admin.site.register(Tag)
admin.site.register(Etapa)
admin.site.register(Pendencia)
