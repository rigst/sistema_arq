from django.apps import AppConfig


class NotificacoesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notificacoes"
    verbose_name = "Notificações"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import AvisoSistema, Notificacao

            AvisoSistema.objects.filter(empresa=grupo).delete()
            Notificacao.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
