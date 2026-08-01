from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import EmpresaModel, Rastreavel
from projetos.models import Projeto


class Tarefa(EmpresaModel, Rastreavel):
    STATUS_CHOICES = [
        ("aberta", "Aberta"),
        ("andamento", "Em andamento"),
        ("concluida", "Concluída"),
    ]

    titulo = models.CharField(max_length=200, verbose_name="título")
    descricao = models.TextField(blank=True, verbose_name="descrição")
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE, related_name="tarefas", null=True, blank=True
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas",
        verbose_name="responsável",
    )
    fornecedor = models.ForeignKey(
        "fornecedores.Fornecedor",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas",
        help_text="Quando quem faz é de fora do escritório.",
    )
    criterio_pronto = models.CharField(max_length=200, blank=True, verbose_name="critério de pronto")
    prazo = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="aberta")

    class Meta:
        ordering = ["status", "prazo", "-id"]
        verbose_name = "tarefa"
        verbose_name_plural = "tarefas"

    def __str__(self):
        return self.titulo

    @property
    def sem_dono(self):
        return self.responsavel_id is None

    @property
    def atrasada(self):
        return bool(self.prazo and self.status != "concluida" and self.prazo < timezone.localdate())


class ApontamentoHora(EmpresaModel):
    """Horas trabalhadas. Com timer: início sem fim = cronômetro rodando."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="apontamentos",
        verbose_name="usuário",
    )
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE, related_name="apontamentos", null=True, blank=True
    )
    tarefa = models.ForeignKey(
        Tarefa, on_delete=models.SET_NULL, related_name="apontamentos", null=True, blank=True
    )
    descricao = models.CharField(max_length=200, blank=True, verbose_name="descrição")
    inicio = models.DateTimeField(default=timezone.now, verbose_name="início")
    fim = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "apontamento de hora"
        verbose_name_plural = "apontamentos de horas"

    def __str__(self):
        return f"{self.usuario} — {self.horas} h"

    @property
    def em_andamento(self):
        return self.fim is None

    @property
    def horas(self):
        fim = self.fim or timezone.now()
        segundos = max((fim - self.inicio).total_seconds(), 0)
        return Decimal(str(round(segundos / 3600, 2)))
