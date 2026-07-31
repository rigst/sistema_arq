from django.apps import AppConfig


class PropostasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "propostas"
    verbose_name = "Propostas"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import ItemProposta, Proposta

            ItemProposta.objects.filter(empresa=grupo).delete()
            Proposta.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
