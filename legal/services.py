from django.utils import timezone

from core.request import ip_cliente

from .models import AceiteLegal, DocumentoLegal


def ip_do_pedido(request) -> str:
    return ip_cliente(request)


def documento_vigente(tipo: str):
    """Versão em vigor de um tipo: a de maior `vigente_desde` já alcançado."""
    agora = timezone.now()
    return (
        DocumentoLegal.objects.filter(tipo=tipo, vigente_desde__lte=agora)
        .order_by("-vigente_desde")
        .first()
    )


def documentos_vigentes():
    vigentes = [documento_vigente(tipo) for tipo, _ in DocumentoLegal.TIPO_CHOICES]
    return [d for d in vigentes if d is not None]


def documentos_pendentes(usuario):
    """Documentos em vigor que este usuário ainda não aceitou."""
    if not usuario or not usuario.is_authenticated:
        return []
    vigentes = documentos_vigentes()
    if not vigentes:
        return []
    ja_aceitos = set(
        AceiteLegal.objects.filter(usuario=usuario, documento__in=vigentes).values_list(
            "documento_id", flat=True
        )
    )
    return [d for d in vigentes if d.pk not in ja_aceitos]


def registrar_aceites(usuario, documentos, request):
    """Grava um aceite por documento, com data, IP e navegador."""
    agente = (request.META.get("HTTP_USER_AGENT") or "")[:400]
    ip = ip_do_pedido(request) or None
    agora = timezone.now()
    criados = []
    for documento in documentos:
        aceite, criado = AceiteLegal.objects.get_or_create(
            usuario=usuario,
            documento=documento,
            defaults={"aceito_em": agora, "ip": ip, "user_agent": agente},
        )
        if criado:
            criados.append(aceite)
    return criados
