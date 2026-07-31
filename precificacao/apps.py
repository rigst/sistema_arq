from django.apps import AppConfig


class PrecificacaoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "precificacao"
    verbose_name = "Precificação"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import ConfiguracaoPrecificacao, CustoFixo, FatorPrecificacao

            CustoFixo.objects.filter(empresa=grupo).delete()
            FatorPrecificacao.objects.filter(empresa=grupo).delete()
            ConfiguracaoPrecificacao.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
