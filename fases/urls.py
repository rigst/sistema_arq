from django.urls import path

from . import views

urlpatterns = [
    path("<int:pk>/", views.detalhe, name="fase_detalhe"),
    path("<int:pk>/iniciar/", views.iniciar, name="fase_iniciar"),
    path("<int:pk>/enviar/", views.enviar, name="fase_enviar"),
    path("<int:pk>/responder/", views.responder, name="fase_responder"),
    path("<int:pk>/concluir/", views.concluir, name="fase_concluir"),
    path("<int:pk>/ajustar/", views.ajustar, name="fase_ajustar"),
    path("<int:pk>/registro/", views.comentar, name="fase_comentar"),
    path("<int:pk>/anexar/", views.anexar, name="fase_anexar"),
    path("<int:pk>/remover/", views.remover_complementar, name="fase_remover"),
    path(
        "projeto/<int:projeto_pk>/complementar/",
        views.ativar_complementar,
        name="fase_ativar_complementar",
    ),
    path("arquivo/<int:pk>/", views.ver_arquivo, name="fase_arquivo_ver"),
    path("arquivo/<int:pk>/editar/", views.renomear_arquivo, name="fase_arquivo_editar"),
    path("arquivo/<int:pk>/remover/", views.remover_arquivo, name="fase_arquivo_remover"),
]
