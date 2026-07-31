from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_tarefas, name="tarefas_lista"),
    path("<int:pk>/concluir/", views.concluir_tarefa, name="tarefa_concluir"),
    path("timer/iniciar/", views.iniciar_timer, name="timer_iniciar"),
    path("timer/parar/", views.parar_timer, name="timer_parar"),
]
