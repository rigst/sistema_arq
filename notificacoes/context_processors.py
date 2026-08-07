def notificacoes_context(request):
    """Contagem de notificações não lidas para o sino na barra superior."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    from core.tenancy import queryset_da_empresa

    from .models import Notificacao

    try:
        total = queryset_da_empresa(Notificacao.objects.filter(lida=False), user).count()
    except Exception:
        total = 0
    return {"notificacoes_nao_lidas": total}
