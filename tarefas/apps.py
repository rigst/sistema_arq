from django.apps import AppConfig


class TarefasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tarefas"
    verbose_name = "Tarefas e horas"

    def ready(self):
        from core.visitante_cleanup import registrar_limpeza

        def _limpar(grupo):
            from .models import ApontamentoHora, Tarefa

            ApontamentoHora.objects.filter(empresa=grupo).delete()
            Tarefa.objects.filter(empresa=grupo).delete()

        registrar_limpeza(_limpar)
