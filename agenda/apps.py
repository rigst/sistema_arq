from django.apps import AppConfig


class AgendaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "agenda"
    verbose_name = "Agenda"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import Compromisso

            Compromisso.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
