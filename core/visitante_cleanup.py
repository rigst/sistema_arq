"""Registro central de limpeza de dados de visitante.

Como o sistema terá muitos módulos (crm, projetos, financeiro, obras, ...),
cada app registra aqui uma função que apaga *seus* dados de um tenant (grupo da
empresa). Assim, quando um visitante se autoexclui, nenhuma tabela é esquecida.

Uso, no `apps.py` de cada módulo de negócio:

    from django.apps import AppConfig
    from core.visitante_cleanup import registrar_limpeza

    class CrmConfig(AppConfig):
        name = "crm"
        def ready(self):
            def _limpar(grupo):
                from .models import Cliente
                Cliente.objects.filter(empresa=grupo).delete()
            registrar_limpeza(_limpar)
"""

import logging

logger = logging.getLogger(__name__)

_LIMPADORES = []


def registrar_limpeza(func):
    """Registra uma função `func(grupo)` que apaga os dados de um módulo para o
    tenant informado. Idempotente por identidade de função."""
    if func not in _LIMPADORES:
        _LIMPADORES.append(func)
    return func


def limpar_dados_negocio(grupo):
    """Executa todos os limpadores registrados para o grupo/empresa dado."""
    if grupo is None:
        return
    for func in list(_LIMPADORES):
        try:
            func(grupo)
        except Exception:
            logger.exception("Falha ao limpar dados de visitante", extra={"limpador": repr(func)})
