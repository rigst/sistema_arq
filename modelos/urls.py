from django.urls import path

from . import views

urlpatterns = [path("", views.indice, name="modelos")]
