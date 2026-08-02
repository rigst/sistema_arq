from django.urls import path

from . import views

urlpatterns = [
    path("", views.agenda, name="agenda"),
    path("<int:pk>/editar/", views.editar_compromisso, name="agenda_editar"),
    path("<int:pk>/remover/", views.remover_compromisso, name="agenda_remover"),
]
