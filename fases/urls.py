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
    path("registro/<int:pk>/soltar/", views.soltar_registro, name="fase_soltar_registro"),
    path("<int:pk>/anexar/", views.anexar, name="fase_anexar"),
    path("<int:pk>/tarefa/", views.nova_tarefa, name="fase_nova_tarefa"),
    path("lembrete/<int:pk>/editar/", views.editar_lembrete, name="lembrete_editar"),
    path("lembrete/<int:pk>/remover/", views.remover_lembrete, name="lembrete_remover"),
    path(
        "projeto/<int:projeto_pk>/lembrete/",
        views.lembrete_do_projeto,
        name="projeto_lembrete",
    ),
    path(
        "projeto/<int:projeto_pk>/complementares/",
        views.editar_complementares,
        name="fase_editar_complementares",
    ),
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
