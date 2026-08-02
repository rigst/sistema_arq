from django.urls import path

from . import views

urlpatterns = [
    # Seção própria: os roteiros de perguntas do escritório.
    path("", views.templates_lista, name="briefing_templates"),
    path("padroes/", views.semear_padroes, name="briefing_semear_padroes"),
    path("roteiro/novo/", views.template_novo, name="briefing_template_novo"),
    path("roteiro/<int:pk>/", views.template_detalhe, name="briefing_template_detalhe"),
    path("roteiro/<int:pk>/pergunta/", views.template_add_pergunta, name="briefing_add_pergunta"),
    path(
        "pergunta/<int:pk>/remover/",
        views.template_remove_pergunta,
        name="briefing_remove_pergunta",
    ),
    # Briefing de um projeto.
    path("projeto/<int:projeto_pk>/", views.editar_briefing, name="briefing_projeto"),
    path("projeto/<int:projeto_pk>/blocos/", views.salvar_blocos, name="briefing_salvar_blocos"),
    path("projeto/<int:projeto_pk>/responder/", views.responder, name="briefing_responder"),
    path(
        "projeto/<int:projeto_pk>/roteiro/",
        views.aplicar_template,
        name="briefing_aplicar_template",
    ),
    path("projeto/<int:projeto_pk>/leitura-ia/", views.leitura_ia, name="briefing_leitura_ia"),
    path(
        "projeto/<int:projeto_pk>/ambiente/",
        views.adicionar_ambiente,
        name="briefing_add_ambiente",
    ),
    path("ambiente/<int:pk>/remover/", views.remover_ambiente, name="briefing_remove_ambiente"),
]
