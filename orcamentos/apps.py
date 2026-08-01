from django.apps import AppConfig


class OrcamentosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orcamentos"
    verbose_name = "Orçamentos"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import ItemOrcamento, Orcamento

            ItemOrcamento.objects.filter(empresa=grupo).delete()
            Orcamento.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
