from django.urls import path

from . import views

urlpatterns = [
    path("", views.painel_projetos, name="projetos_painel"),
    path("novo/", views.novo_projeto, name="projeto_novo"),
    path("<int:pk>/", views.detalhe_projeto, name="projeto_detalhe"),
    path("<int:pk>/editar/", views.editar_projeto, name="projeto_editar"),
    path("<int:pk>/pendencia/", views.adicionar_pendencia, name="projeto_add_pendencia"),
    path("etapa/<int:pk>/avancar/", views.avancar_etapa, name="etapa_avancar"),
    path("pendencia/<int:pk>/resolver/", views.resolver_pendencia, name="pendencia_resolver"),
]
