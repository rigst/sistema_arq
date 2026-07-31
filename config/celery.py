import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("sistema_arq")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Agendamentos periódicos (Celery Beat).
app.conf.beat_schedule = {
    "limpar-visitantes-expirados": {
        "task": "usuarios.tasks.limpar_visitantes_expirados_task",
        "schedule": 60 * 60,  # de hora em hora
    },
    "varrer-alertas": {
        "task": "notificacoes.tasks.varrer_alertas_task",
        "schedule": 60 * 60 * 12,  # duas vezes ao dia
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
