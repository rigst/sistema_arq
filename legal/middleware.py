from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode

from .services import documentos_pendentes

# Caminhos que continuam acessíveis com aceite pendente: a própria tela de
# aceite, os documentos, sair, o admin e os arquivos servidos pelo Django.
PREFIXOS_LIVRES = ("/aceite/", "/termos/", "/privacidade/", "/logout/", "/login/", "/admin/", "/static/", "/media/")


class AceiteLegalMiddleware:
    """Enquanto houver documento em vigor não aceito, o usuário logado só
    navega para a tela de aceite. Publicar uma versão nova recoloca todo
    mundo nessa tela."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        if (
            usuario is not None
            and getattr(usuario, "is_authenticated", False)
            and not request.path.startswith(PREFIXOS_LIVRES)
            and documentos_pendentes(usuario)
        ):
            destino = reverse("aceite_legal")
            if request.method == "GET":
                destino = f"{destino}?{urlencode({'next': request.get_full_path()})}"
            return redirect(destino)
        return self.get_response(request)
