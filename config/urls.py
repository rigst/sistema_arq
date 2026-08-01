from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from usuarios.views import UsuarioLoginView, UsuarioLogoutView

urlpatterns = [
    path(
        "favicon.ico",
        RedirectView.as_view(url=settings.STATIC_URL + "favicon.ico", permanent=True),
    ),
    path("admin/", admin.site.urls),
    path("login/", UsuarioLoginView.as_view(), name="login"),
    path("logout/", UsuarioLogoutView.as_view(), name="logout"),
    path("", include("legal.urls")),
    path("", include("core.urls")),
    path("clientes/", include("crm.urls")),
    path("precificacao/", include("precificacao.urls")),
    path("propostas/", include("propostas.urls")),
    path("projetos/", include("projetos.urls")),
    path("tarefas/", include("tarefas.urls")),
    path("financeiro/", include("financeiro.urls")),
    path("contratos/", include("contratos.urls")),
    path("briefing/", include("briefing.urls")),
    path("agenda/", include("agenda.urls")),
    path("obras/", include("obras.urls")),
    path("regulatorio/", include("regulatorio.urls")),
    path("notificacoes/", include("notificacoes.urls")),
    path("diagnostico/", include("diagnostico.urls")),
    path("onboarding/", include("onboarding.urls")),
]

if settings.DEBUG and settings.DEBUG_EXPOSE_MEDIA:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
