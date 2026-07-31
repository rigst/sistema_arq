from celery import shared_task

from .visitantes import limpar_visitantes_expirados


@shared_task(ignore_result=True)
def limpar_visitantes_expirados_task():
    """Task agendada (Celery Beat) que remove visitantes que passaram do TTL."""
    return limpar_visitantes_expirados()
