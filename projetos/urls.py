from django.urls import path

from . import views

urlpatterns = [
    path("", views.painel_projetos, name="projetos_painel"),
    path("<int:pk>/", views.detalhe_projeto, name="projeto_detalhe"),
    path("<int:pk>/editar/", views.editar_projeto, name="projeto_editar"),
    path("<int:pk>/planejamento/", views.atualizar_planejamento, name="projeto_planejamento"),
    path("tarefa/<int:pk>/alternar/", views.alternar_tarefa, name="projeto_tarefa_alternar"),
]
