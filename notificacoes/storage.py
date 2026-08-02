"""Armazenamento de mensagens que também guarda o que foi dito.

O toast do canto vive alguns segundos. Quando some no momento em que a pessoa
desviou o olho, a única saída hoje é refazer a ação para ver de novo o que
apareceu. Trocando o storage padrão do Django, todo `messages.success(...)` que
já existe no sistema passa a deixar rastro — sem precisar tocar em nenhuma das
dezenas de chamadas espalhadas pelas views.

Falha aqui não pode derrubar a requisição: o aviso é acessório, e perder o
histórico é bem menos grave do que devolver erro 500 depois de salvar.
"""

import logging

from django.contrib.messages import constants
from django.contrib.messages.storage.fallback import FallbackStorage

logger = logging.getLogger(__name__)

NIVEL_POR_CONSTANTE = {
    constants.DEBUG: "sucesso",
    constants.INFO: "atencao",
    constants.SUCCESS: "sucesso",
    constants.WARNING: "atencao",
    constants.ERROR: "erro",
}


class ArmazenamentoComHistorico(FallbackStorage):
    def add(self, level, message, extra_tags=""):
        super().add(level, message, extra_tags)
        self._guardar(level, message)

    def _guardar(self, level, message):
        request = self.request
        usuario = getattr(request, "user", None)
        if usuario is None or not getattr(usuario, "is_authenticated", False):
            return
        try:
            from core.tenancy import obter_grupo_empresa_usuario

            from .models import AvisoSistema

            grupo = obter_grupo_empresa_usuario(usuario)
            if grupo is None:
                return
            AvisoSistema.objects.create(
                empresa=grupo,
                usuario=usuario,
                nivel=NIVEL_POR_CONSTANTE.get(level, "sucesso"),
                texto=str(message)[:300],
            )
        except Exception:
            logger.warning("Não foi possível guardar o aviso no histórico.", exc_info=True)
