import ipaddress

from django.conf import settings


def ip_cliente(request) -> str:
    """Só confia no proxy quando a implantação declarou essa topologia."""
    candidatos = []
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        candidatos.extend(request.META.get("HTTP_X_FORWARDED_FOR", "").split(","))
    candidatos.append(request.META.get("REMOTE_ADDR", ""))
    for candidato in candidatos:
        candidato = candidato.strip()
        try:
            return str(ipaddress.ip_address(candidato))
        except ValueError:
            continue
    return ""
