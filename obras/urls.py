from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_obras, name="obras_lista"),
    path("nova/", views.nova_obra, name="obra_nova"),
    path("<int:pk>/", views.detalhe_obra, name="obra_detalhe"),
    path("<int:pk>/editar/", views.editar_obra, name="obra_editar"),
    path("<int:pk>/etapa/", views.adicionar_etapa, name="obra_etapa"),
    path("<int:pk>/visita/", views.registrar_visita, name="obra_visita"),
    path("<int:pk>/medicao/", views.registrar_medicao, name="obra_medicao"),
    path("etapa/<int:pk>/avanco/", views.atualizar_avanco, name="obra_avanco"),
    path("medicao/<int:pk>/aprovar/", views.aprovar_medicao_view, name="medicao_aprovar"),
]
