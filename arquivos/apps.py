from django.apps import AppConfig


class ArquivosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "arquivos"
    verbose_name = "Arquivos"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import Arquivo

            # delete() em queryset não remove o arquivo do disco; percorre um a um.
            for arquivo in Arquivo.objects.filter(empresa=grupo).iterator():
                arquivo.arquivo.delete(save=False)
                arquivo.delete()

        registrar_limpeza(_limpar)
