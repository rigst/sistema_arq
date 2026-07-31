from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_clientes, name="crm_lista"),
    path("novo/", views.novo_cliente, name="crm_novo"),
    path("<int:pk>/", views.detalhe_cliente, name="crm_detalhe"),
    path("<int:pk>/editar/", views.editar_cliente, name="crm_editar"),
    path("<int:pk>/interacao/", views.adicionar_interacao, name="crm_interacao"),
]
