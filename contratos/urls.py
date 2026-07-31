from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_contratos, name="contratos_lista"),
    path("novo/", views.novo_contrato, name="contrato_novo"),
    path("<int:pk>/", views.detalhe_contrato, name="contrato_detalhe"),
    path("<int:pk>/editar/", views.editar_contrato, name="contrato_editar"),
    path("<int:pk>/parcelas/", views.gerar_parcelas_view, name="contrato_gerar_parcelas"),
    path("<int:pk>/lancar/", views.lancar_financeiro, name="contrato_lancar"),
    path("<int:pk>/alteracao/", views.registrar_alteracao, name="contrato_alteracao"),
    path("<int:pk>/documento/", views.enviar_documento, name="contrato_documento"),
    path("parcela/<int:pk>/alternar/", views.alternar_parcela, name="parcela_alternar"),
]
