from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "crm"
    verbose_name = "CRM"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import Cliente, Interacao

            Interacao.objects.filter(empresa=grupo).delete()
            Cliente.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
