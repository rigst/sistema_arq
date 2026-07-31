from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.tenancy import queryset_da_empresa

from .models import Notificacao


@login_required
def lista_notificacoes(request):
    notificacoes = queryset_da_empresa(Notificacao.objects.all(), request.user)
    return render(
        request,
        "notificacoes/lista.html",
        {
            "notificacoes": notificacoes,
            "nao_lidas": [n for n in notificacoes if not n.lida],
        },
    )


@require_POST
@login_required
def marcar_lida(request, pk):
    notificacao = get_object_or_404(
        queryset_da_empresa(Notificacao.objects.all(), request.user), pk=pk
    )
    notificacao.lida = True
    notificacao.save(update_fields=["lida"])
    if notificacao.url:
        return redirect(notificacao.url)
    return redirect("notificacoes_lista")


@require_POST
@login_required
def marcar_todas(request):
    queryset_da_empresa(Notificacao.objects.filter(lida=False), request.user).update(lida=True)
    return redirect("notificacoes_lista")
