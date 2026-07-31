from django.apps import AppConfig


class RegulatorioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "regulatorio"
    verbose_name = "Regulatório"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import ObrigacaoTecnica

            ObrigacaoTecnica.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
