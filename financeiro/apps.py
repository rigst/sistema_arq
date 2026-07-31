from django.apps import AppConfig


class FinanceiroConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "financeiro"
    verbose_name = "Financeiro"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import Categoria, ContaBancaria, Lancamento

            Lancamento.objects.filter(empresa=grupo).delete()
            Categoria.objects.filter(empresa=grupo).delete()
            ContaBancaria.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
