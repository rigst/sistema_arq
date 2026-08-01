from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista, name="orcamentos_lista"),
    path("projeto/<int:projeto_pk>/novo/", views.novo, name="orcamento_novo"),
    path("<int:pk>/", views.detalhe, name="orcamento_detalhe"),
    path("<int:pk>/item/", views.adicionar_item, name="orcamento_add_item"),
    path("item/<int:pk>/remover/", views.remover_item, name="orcamento_remove_item"),
    path("item/<int:pk>/realizado/", views.registrar_realizado, name="orcamento_item_realizado"),
]
