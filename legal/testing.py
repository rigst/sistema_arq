"""Atalho para testes de outros apps.

Com o AceiteLegalMiddleware no ar, um usuário recém-criado é desviado para a
tela de aceite. Testes que só querem exercitar uma view de negócio chamam
`aceitar_documentos(user)` depois do login.
"""

from .models import AceiteLegal
from .services import documentos_vigentes


def aceitar_documentos(usuario, ip="127.0.0.1", user_agent="testes"):
    for documento in documentos_vigentes():
        AceiteLegal.objects.get_or_create(
            usuario=usuario, documento=documento, defaults={"ip": ip, "user_agent": user_agent}
        )
