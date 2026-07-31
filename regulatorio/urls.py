from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_obrigacoes, name="regulatorio_lista"),
    path("nova/", views.nova_obrigacao, name="regulatorio_nova"),
    path("<int:pk>/editar/", views.editar_obrigacao, name="regulatorio_editar"),
    path("<int:pk>/baixar/", views.baixar_obrigacao, name="regulatorio_baixar"),
]
