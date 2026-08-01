from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_contratos, name="contratos_lista"),
    path("novo/", views.novo_contrato, name="contrato_novo"),
    path("<int:pk>/", views.detalhe_contrato, name="contrato_detalhe"),
    path("<int:pk>/editar/", views.editar_contrato, name="contrato_editar"),
    path("<int:pk>/pdf/", views.contrato_pdf, name="contrato_pdf"),
    path("<int:pk>/parcelas/", views.gerar_parcelas_view, name="contrato_gerar_parcelas"),
    path("<int:pk>/lancar/", views.lancar_financeiro, name="contrato_lancar"),
    path("<int:pk>/alteracao/", views.registrar_alteracao, name="contrato_alteracao"),
    path("<int:pk>/documento/", views.enviar_documento, name="contrato_documento"),
    path("parcela/<int:pk>/alternar/", views.alternar_parcela, name="parcela_alternar"),
    # Modelos de contrato e redação da minuta.
    path("modelos/", views.modelos_lista, name="contratos_modelos"),
    path("modelos/padroes/", views.modelos_semear, name="contratos_modelos_padroes"),
    path("modelos/novo/", views.modelo_editar, name="contrato_modelo_novo"),
    path("modelos/<int:pk>/", views.modelo_editar, name="contrato_modelo_editar"),
    path("modelos/<int:pk>/remover/", views.modelo_remover, name="contrato_modelo_remover"),
    path("<int:pk>/redigir/", views.redigir, name="contrato_redigir"),
]
