from decimal import Decimal

from django.db import models

from core.models import EmpresaModel, Rastreavel
from crm.models import Cliente


class Proposta(EmpresaModel, Rastreavel):
    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("enviada", "Enviada"),
        ("aprovada", "Aprovada"),
        ("rejeitada", "Rejeitada"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="propostas")
    titulo = models.CharField(max_length=200)
    tipo_projeto = models.CharField(max_length=20, default="residencial")
    hora_tecnica_aplicada = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="rascunho")
    validade = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    # Projeto gerado ao aprovar (elo da jornada Proposta → Projeto).
    projeto_gerado = models.OneToOneField(
        "projetos.Projeto", on_delete=models.SET_NULL, null=True, blank=True, related_name="proposta_origem"
    )

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "proposta"
        verbose_name_plural = "propostas"

    def __str__(self):
        return self.titulo

    @property
    def valor_total(self):
        return sum((item.valor for item in self.itens.all()), Decimal("0"))


class ItemProposta(EmpresaModel):
    """Ambiente/etapa da proposta com horas estimadas e valor calculado."""

    proposta = models.ForeignKey(Proposta, on_delete=models.CASCADE, related_name="itens")
    descricao = models.CharField(max_length=200)
    horas_estimadas = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "id"]

    def __str__(self):
        return self.descricao
