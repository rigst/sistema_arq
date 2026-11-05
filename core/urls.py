from django.urls import path

from .healthz import healthz
from .views import alternar_empresa, dashboard, identidade, imagem_identidade

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("", dashboard, name="dashboard"),
    path("empresa/alternar/", alternar_empresa, name="alternar_empresa"),
    path("escritorio/identidade/", identidade, name="identidade"),
    path("escritorio/identidade/<str:tipo>/", imagem_identidade, name="identidade_imagem"),
]
