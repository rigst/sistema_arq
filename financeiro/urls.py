from django.urls import path

from . import views

urlpatterns = [
    path("", views.painel_financeiro, name="financeiro_painel"),
    path("conta/nova/", views.nova_conta, name="financeiro_nova_conta"),
    path("dre/", views.dre_view, name="financeiro_dre"),
    path("dre/csv/", views.dre_csv, name="financeiro_dre_csv"),
    path("importar/", views.importar_extrato, name="financeiro_importar"),
]
