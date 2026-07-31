from celery import shared_task

from .services import varrer_todas


@shared_task(ignore_result=True)
def varrer_alertas_task():
    """Task agendada (Celery Beat, diária) que gera notificações de alerta."""
    return varrer_todas()
