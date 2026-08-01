from django.apps import AppConfig


class BriefingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "briefing"
    verbose_name = "Briefing"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import (
                AmbientePrograma,
                Briefing,
                OpcaoPergunta,
                PerguntaTemplate,
                RespostaBriefing,
                TemplateBriefing,
            )

            RespostaBriefing.objects.filter(empresa=grupo).delete()
            OpcaoPergunta.objects.filter(empresa=grupo).delete()
            PerguntaTemplate.objects.filter(empresa=grupo).delete()
            TemplateBriefing.objects.filter(empresa=grupo).delete()
            AmbientePrograma.objects.filter(empresa=grupo).delete()
            Briefing.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
