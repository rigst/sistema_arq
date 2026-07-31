from django.urls import path

from . import views

urlpatterns = [
    path("", views.painel_precificacao, name="precificacao"),
    path("custos/adicionar/", views.adicionar_custo, name="precificacao_add_custo"),
    path("custos/<int:pk>/remover/", views.remover_custo, name="precificacao_remove_custo"),
]
