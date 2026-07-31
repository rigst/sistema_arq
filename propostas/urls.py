from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_propostas, name="propostas_lista"),
    path("nova/", views.nova_proposta, name="proposta_nova"),
    path("<int:pk>/", views.detalhe_proposta, name="proposta_detalhe"),
    path("<int:pk>/pdf/", views.proposta_pdf, name="proposta_pdf"),
    path("<int:pk>/hora-tecnica/", views.definir_hora_tecnica, name="proposta_hora_tecnica"),
    path("<int:pk>/item/", views.adicionar_item, name="proposta_add_item"),
    path("<int:pk>/aprovar/", views.aprovar_proposta, name="proposta_aprovar"),
    path("item/<int:pk>/remover/", views.remover_item, name="proposta_remove_item"),
]
