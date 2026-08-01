from django.apps import AppConfig


class ContratosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contratos"
    verbose_name = "Contratos"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import (
                AlteracaoEscopo,
                Contrato,
                Documento,
                ModeloContrato,
                Parcela,
            )

            Documento.objects.filter(empresa=grupo).delete()
            AlteracaoEscopo.objects.filter(empresa=grupo).delete()
            Parcela.objects.filter(empresa=grupo).delete()
            Contrato.objects.filter(empresa=grupo).delete()
            ModeloContrato.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
