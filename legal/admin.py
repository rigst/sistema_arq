from django.contrib import admin

from .models import AceiteLegal, DocumentoLegal


@admin.register(DocumentoLegal)
class DocumentoLegalAdmin(admin.ModelAdmin):
    list_display = ("tipo", "versao", "titulo", "vigente_desde", "total_aceites")
    list_filter = ("tipo",)
    search_fields = ("titulo", "versao", "conteudo")
    readonly_fields = ("criado_em", "atualizado_em")

    @admin.display(description="aceites")
    def total_aceites(self, obj):
        return obj.aceites.count()


@admin.register(AceiteLegal)
class AceiteLegalAdmin(admin.ModelAdmin):
    """Registro de auditoria: só leitura, nem no admin se edita um aceite."""

    list_display = ("usuario", "documento", "aceito_em", "ip")
    list_filter = ("documento__tipo", "documento__versao")
    search_fields = ("usuario__username", "ip", "user_agent")
    readonly_fields = ("usuario", "documento", "aceito_em", "ip", "user_agent")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
