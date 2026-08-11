from django.contrib import admin

from .models import Empresa


def acesso_admin_restrito(request):
    """O admin global não aplica o filtro de tenant das telas do produto."""
    return bool(request.user.is_active and request.user.is_superuser)


# Troca deliberada de um método da instância global do admin — é assim que se
# restringe o acesso sem subclassear AdminSite e reconfigurar as URLs. O ignore
# é do código exato dessa troca, não uma supressão ampla.
admin.site.has_permission = acesso_admin_restrito  # type: ignore[method-assign]
admin.site.site_header = "Administração do A.R.Q."
admin.site.site_title = "A.R.Q. Admin"
admin.site.index_title = "Cadastros e configuração"


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nome", "grupo", "ativa", "criada_em")
    list_filter = ("ativa",)
    search_fields = ("nome",)
    readonly_fields = ("criada_em", "atualizada_em")
