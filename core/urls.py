from django.urls import path

from .views import alternar_empresa, dashboard, healthz, identidade

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("", dashboard, name="dashboard"),
    path("empresa/alternar/", alternar_empresa, name="alternar_empresa"),
    path("escritorio/identidade/", identidade, name="identidade"),
]
