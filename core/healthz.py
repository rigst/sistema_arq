"""Sonda de saúde para o smoke-test do CD (rigst/ci RUNBOOK.md, seção 7.8).

Responde 200 só quando o processo consegue usar o que precisa para servir uma
página: banco, cache e o broker do Celery. Qualquer falha vira 503, que o
deploy/cd-deploy.sh trata como deploy quebrado e reverte.

O corpo é só {"status": "ok"} ou {"status": "indisponivel"}: qual componente
caiu fica no log, não na resposta.

Com DJANGO_HEALTHZ_TOKEN definido, a rota exige o header X-Healthz-Token e
responde 404 sem ele — o cd-deploy.sh monta o header depois de carregar o .env.

Não cobre worker do Celery parado: perguntar aos workers (`control.ping`)
custa um round-trip por chamada. Worker parado é assunto do systemd
(Restart=) e do Sentry.

A rota não passa pelo login, e o AceiteLegalMiddleware só intercepta usuário
autenticado, coisa que o curl do deploy nunca é.
"""

import logging
import secrets
import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpResponseNotFound, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

logger = logging.getLogger(__name__)


def _banco():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def _cache():
    chave = f"healthz:{uuid.uuid4().hex}"
    cache.set(chave, "1", 10)
    if cache.get(chave) != "1":
        raise RuntimeError("cache não devolveu o valor gravado")
    cache.delete(chave)


def _broker():
    # Sem broker (desenvolvimento, testes) as tarefas rodam eager: não há o
    # que sondar.
    if not getattr(settings, "CELERY_BROKER_URL", ""):
        return
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        return
    from config.celery import app

    with app.connection_for_write() as conexao:
        conexao.ensure_connection(max_retries=1, timeout=3)


VERIFICACOES = (("banco", _banco), ("cache", _cache), ("broker", _broker))


def _token_valido(request):
    esperado = getattr(settings, "HEALTHZ_TOKEN", "")
    if not esperado:
        return True
    recebido = request.headers.get("X-Healthz-Token", "").strip()
    return bool(recebido) and secrets.compare_digest(recebido, esperado)


@never_cache
@require_safe
def healthz(request):
    if not _token_valido(request):
        return HttpResponseNotFound()
    falhas = []
    for nome, verificar in VERIFICACOES:
        try:
            verificar()
        except Exception:  # sonda: qualquer falha é "indisponível", e vai para o log
            logger.exception("healthz: %s indisponível", nome)
            falhas.append(nome)
    if falhas:
        return JsonResponse({"status": "indisponivel"}, status=503)
    return JsonResponse({"status": "ok"})
