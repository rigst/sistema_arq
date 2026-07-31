from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_notificacoes, name="notificacoes_lista"),
    path("<int:pk>/lida/", views.marcar_lida, name="notificacao_lida"),
    path("todas/", views.marcar_todas, name="notificacoes_todas"),
]
