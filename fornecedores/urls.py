from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista, name="fornecedores_lista"),
    path("novo/", views.novo, name="fornecedor_novo"),
    path("<int:pk>/editar/", views.editar, name="fornecedor_editar"),
    path("<int:pk>/remover/", views.remover, name="fornecedor_remover"),
]
