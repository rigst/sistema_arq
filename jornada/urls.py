from django.urls import path

from . import views

urlpatterns = [
    path("novo/", views.abrir, name="jornada_abrir"),
    path("<int:projeto_pk>/", views.roteiro, name="jornada_roteiro"),
]
