from django.apps import AppConfig


class ObrasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "obras"
    verbose_name = "Obras"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import EtapaObra, Medicao, Obra, VisitaTecnica

            Medicao.objects.filter(empresa=grupo).delete()
            VisitaTecnica.objects.filter(empresa=grupo).delete()
            EtapaObra.objects.filter(empresa=grupo).delete()
            Obra.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
