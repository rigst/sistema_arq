from django.urls import path

from . import views

urlpatterns = [
    path("termos/", views.termos, name="termos"),
    path("privacidade/", views.privacidade, name="privacidade"),
    path("aceite/", views.aceite, name="aceite_legal"),
]
