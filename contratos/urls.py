from django.urls import path

from . import views

urlpatterns = [
    path("novo/", views.novo_contrato, name="contrato_novo"),
    path("<int:pk>/", views.detalhe_contrato, name="contrato_detalhe"),
    path("<int:pk>/enviar/", views.enviar_contrato, name="contrato_enviar"),
    path("<int:pk>/retornar/", views.retornar_para_ajustes, name="contrato_retornar"),
    path("<int:pk>/aprovar/", views.aprovar_contrato, name="contrato_aprovar"),
    path("<int:pk>/pdf/", views.contrato_pdf, name="contrato_pdf"),
    path("<int:pk>/parcelas/", views.gerar_parcelas_view, name="contrato_gerar_parcelas"),
    path("<int:pk>/parcela/", views.adicionar_parcela, name="contrato_parcela_adicionar"),
    path("<int:pk>/lancar/", views.lancar_financeiro, name="contrato_lancar"),
    path("<int:pk>/alteracao/", views.registrar_alteracao, name="contrato_alteracao"),
    path("<int:pk>/documento/", views.enviar_documento, name="contrato_documento"),
    path("documento/<int:pk>/remover/", views.remover_documento, name="contrato_documento_remover"),
    path("documento/<int:pk>/baixar/", views.baixar_documento, name="contrato_documento_baixar"),
    path("parcela/<int:pk>/alternar/", views.alternar_parcela, name="parcela_alternar"),
    path("parcela/<int:pk>/editar/", views.editar_parcela, name="parcela_editar"),
    path("parcela/<int:pk>/linha/", views.linha_parcela, name="parcela_linha"),
    path("parcela/<int:pk>/remover/", views.remover_parcela, name="parcela_remover"),
    path("alteracao/<int:pk>/editar/", views.editar_alteracao, name="contrato_alteracao_editar"),
    path("alteracao/<int:pk>/linha/", views.linha_alteracao, name="contrato_alteracao_linha"),
    path("alteracao/<int:pk>/remover/", views.remover_alteracao, name="contrato_alteracao_remover"),
    path("documento/<int:pk>/editar/", views.editar_documento, name="contrato_documento_editar"),
    path("documento/<int:pk>/linha/", views.linha_documento, name="contrato_documento_linha"),
    # Modelos de contrato e redação da minuta.
    path("modelos/", views.modelos_lista, name="contratos_modelos"),
    path("modelos/padroes/", views.modelos_semear, name="contratos_modelos_padroes"),
    path("modelos/novo/", views.modelo_editar, name="contrato_modelo_novo"),
    path("modelos/<int:pk>/", views.modelo_editar, name="contrato_modelo_editar"),
    path("modelos/<int:pk>/remover/", views.modelo_remover, name="contrato_modelo_remover"),
]
