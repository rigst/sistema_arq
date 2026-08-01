from django.apps import AppConfig


class FornecedoresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fornecedores"
    verbose_name = "Fornecedores"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import Fornecedor

            Fornecedor.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
