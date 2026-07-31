from django.urls import path

from . import views

urlpatterns = [
    path("projeto/<int:projeto_pk>/", views.editar_briefing, name="briefing_projeto"),
    path("projeto/<int:projeto_pk>/ambiente/", views.adicionar_ambiente, name="briefing_add_ambiente"),
    path("ambiente/<int:pk>/remover/", views.remover_ambiente, name="briefing_remove_ambiente"),
]
