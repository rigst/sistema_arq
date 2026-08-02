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
    # A tarefa nasce dentro da fase que a exige: detalhar esquadria é trabalho
    # de executivo, não do projeto em abstrato. Sem fase, é tarefa do projeto.
    fase = models.ForeignKey(
        "fases.Fase", on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas"
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
    """Horas trabalhadas, por cronômetro ou lançadas à mão.

    Três estados, todos derivados de dois campos: `fim` diz se está fechado e
    `pausado_em` diz se o relógio está andando. O tempo parado é descontado por
    `segundos_pausa`, que cresce a cada retomada — assim uma pausa para o
    almoço não entra na conta do cliente.
    """

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
    pausado_em = models.DateTimeField(null=True, blank=True, verbose_name="pausado em")
    segundos_pausa = models.PositiveIntegerField(default=0, verbose_name="segundos em pausa")

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "apontamento de hora"
        verbose_name_plural = "apontamentos de horas"

    def __str__(self):
        return f"{self.usuario} — {self.horas} h"

    @property
    def em_andamento(self):
        """Aberto — rodando ou pausado. É o que impede abrir outro."""
        return self.fim is None

    @property
    def rodando(self):
        return self.fim is None and self.pausado_em is None

    @property
    def pausado(self):
        return self.fim is None and self.pausado_em is not None

    @property
    def segundos(self):
        """Tempo efetivamente trabalhado, sem as pausas."""
        fim = self.fim or timezone.now()
        parado = self.segundos_pausa
        if self.pausado_em:
            # Pausa ainda aberta: conta até agora, ou até o fim se foi parado
            # sem retomar antes.
            parado += max(((self.fim or timezone.now()) - self.pausado_em).total_seconds(), 0)
        return max((fim - self.inicio).total_seconds() - parado, 0)

    @property
    def horas(self):
        return Decimal(str(round(self.segundos / 3600, 2)))

    def pausar(self):
        if self.rodando:
            self.pausado_em = timezone.now()
            self.save(update_fields=["pausado_em"])

    def retomar(self):
        if self.pausado:
            self.segundos_pausa += int((timezone.now() - self.pausado_em).total_seconds())
            self.pausado_em = None
            self.save(update_fields=["segundos_pausa", "pausado_em"])

    def parar(self):
        if self.fim is not None:
            return
        agora = timezone.now()
        if self.pausado_em:
            self.segundos_pausa += int((agora - self.pausado_em).total_seconds())
            self.pausado_em = None
        self.fim = agora
        self.save(update_fields=["fim", "pausado_em", "segundos_pausa"])
