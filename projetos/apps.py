from django.apps import AppConfig


class ProjetosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projetos"
    verbose_name = "Projetos"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import Etapa, Pendencia, Projeto, Tag

            Pendencia.objects.filter(empresa=grupo).delete()
            Etapa.objects.filter(empresa=grupo).delete()
            Projeto.objects.filter(empresa=grupo).delete()
            Tag.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
