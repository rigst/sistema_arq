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
    titulo = models.CharField(max_length=200, verbose_name="título")
    tipo_projeto = models.CharField(max_length=20, default="residencial", verbose_name="tipo de projeto")
    hora_tecnica_aplicada = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="hora técnica aplicada")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="rascunho")
    validade = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True, verbose_name="observações")
    # Fatores de projeto aplicados para chegar à hora técnica desta proposta.
    fatores = models.ManyToManyField(
        "precificacao.FatorPrecificacao", blank=True, related_name="propostas"
    )
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

    @property
    def horas_totais(self):
        return sum((item.horas_estimadas for item in self.itens.all()), Decimal("0"))

    @property
    def editavel(self):
        """Depois de enviada, mexer nos valores é mudar o que o cliente já viu.

        Corrigir continua possível — mas exige voltar a proposta para edição,
        de propósito: o gesto tem de ser deliberado, e fica registrado.
        """
        return self.status == "rascunho"

    @property
    def aguardando_cliente(self):
        return self.status == "enviada"


class ItemProposta(EmpresaModel):
    """Ambiente/etapa da proposta com horas estimadas e valor calculado."""

    proposta = models.ForeignKey(Proposta, on_delete=models.CASCADE, related_name="itens")
    descricao = models.CharField(max_length=200, verbose_name="descrição")
    horas_estimadas = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="horas estimadas")
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "id"]

    def __str__(self):
        return self.descricao
