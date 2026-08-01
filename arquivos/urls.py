from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista, name="arquivos_lista"),
    path("<int:pk>/status/", views.mudar_status, name="arquivo_status"),
    path("<int:pk>/remover/", views.remover, name="arquivo_remover"),
]
