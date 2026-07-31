from django.urls import path

from . import views

urlpatterns = [
    path("", views.painel_financeiro, name="financeiro_painel"),
    path("conta/nova/", views.nova_conta, name="financeiro_nova_conta"),
]
