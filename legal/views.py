from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import DocumentoLegal
from .services import documento_vigente, documentos_pendentes, registrar_aceites


def _documento_publico(request, tipo):
    documento = documento_vigente(tipo)
    if documento is None:
        raise Http404("Documento ainda não publicado.")
    return render(
        request,
        "legal/documento.html",
        {"documento": documento, "outro": _outro_tipo(tipo)},
    )


def _outro_tipo(tipo):
    alvo = (
        DocumentoLegal.PRIVACIDADE if tipo == DocumentoLegal.TERMOS else DocumentoLegal.TERMOS
    )
    return documento_vigente(alvo)


def termos(request):
    return _documento_publico(request, DocumentoLegal.TERMOS)


def privacidade(request):
    return _documento_publico(request, DocumentoLegal.PRIVACIDADE)


@login_required
def aceite(request):
    pendentes = documentos_pendentes(request.user)
    destino = request.GET.get("next") or request.POST.get("next") or ""
    if not url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        destino = reverse("dashboard")

    if not pendentes:
        return redirect(destino)

    if request.method == "POST":
        if request.POST.get("aceito") != "1":
            messages.error(request, "Marque a caixa de aceite para continuar.")
        else:
            registrar_aceites(request.user, pendentes, request)
            messages.success(request, "Aceite registrado. Bom trabalho.")
            return redirect(destino)

    return render(
        request,
        "legal/aceite.html",
        {"pendentes": pendentes, "next": destino, "primeira_vez": _primeiro_aceite(request.user)},
    )


def _primeiro_aceite(usuario):
    return not usuario.aceites_legais.exists()
