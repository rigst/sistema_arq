from django.urls import path

from . import views

urlpatterns = [
    path("<int:pk>/", views.detalhe_proposta, name="proposta_detalhe"),
    path("<int:pk>/pdf/", views.proposta_pdf, name="proposta_pdf"),
    path("<int:pk>/hora-tecnica/", views.definir_hora_tecnica, name="proposta_hora_tecnica"),
    path("<int:pk>/item/", views.adicionar_item, name="proposta_add_item"),
    path("<int:pk>/prontos/", views.adicionar_prontos, name="proposta_add_prontos"),
    path("<int:pk>/finalizar/", views.finalizar_proposta, name="proposta_finalizar"),
    path("<int:pk>/aprovar/", views.aprovar_proposta, name="proposta_aprovar"),
    path("<int:pk>/reabrir/", views.reabrir_proposta, name="proposta_reabrir"),
    path("item/<int:pk>/editar/", views.editar_item, name="proposta_item_editar"),
    path("item/<int:pk>/linha/", views.linha_item, name="proposta_item_linha"),
    path("item/<int:pk>/remover/", views.remover_item, name="proposta_remove_item"),
    path("item/<int:pk>/mover/", views.mover_item, name="proposta_mover_item"),
]
