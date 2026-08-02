from django.apps import AppConfig


class FasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fases"
    verbose_name = "Fases do projeto"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import Fase, Lembrete

            Lembrete.objects.filter(empresa=grupo).delete()
            Fase.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
