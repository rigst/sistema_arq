from django.contrib import admin

from .models import Cliente, Interacao


class InteracaoInline(admin.TabularInline):
    model = Interacao
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "fase", "origem", "email", "telefone", "ativo", "empresa")
    list_filter = ("fase", "origem", "ativo")
    search_fields = ("nome", "email", "telefone")
    inlines = [InteracaoInline]


@admin.register(Interacao)
class InteracaoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "tipo", "criado_em", "autor")
    list_filter = ("tipo",)
