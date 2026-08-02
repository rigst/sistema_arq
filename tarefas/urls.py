from django.urls import path

from . import views

urlpatterns = [
    path("<int:pk>/concluir/", views.concluir_tarefa, name="tarefa_concluir"),
    path("timer/iniciar/", views.iniciar_timer, name="timer_iniciar"),
    path("timer/pausar/", views.pausar_timer, name="timer_pausar"),
    path("timer/parar/", views.parar_timer, name="timer_parar"),
    # Horas lançadas à mão, dentro do projeto a que pertencem.
    path("horas/projeto/<int:projeto_pk>/", views.apontar_hora, name="hora_apontar"),
    path("horas/<int:pk>/editar/", views.editar_apontamento, name="hora_editar"),
    path("horas/<int:pk>/remover/", views.remover_apontamento, name="hora_remover"),
]
