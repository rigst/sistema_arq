from django.db import models

from core.models import EmpresaModel, Rastreavel
from projetos.models import Projeto


class ContaBancaria(EmpresaModel):
    nome = models.CharField(max_length=100)
    saldo_inicial = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="saldo inicial"
    )
    pessoal = models.BooleanField(
        default=False, help_text="Marque para separar o caixa pessoal do escritório."
    )

    class Meta:
        ordering = ["nome"]
        verbose_name = "conta bancária"
        verbose_name_plural = "contas bancárias"

    def __str__(self):
        return self.nome


class Categoria(EmpresaModel):
    TIPO_CHOICES = [("entrada", "Entrada"), ("saida", "Saída")]
    nome = models.CharField(max_length=80)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default="saida")

    class Meta:
        ordering = ["tipo", "nome"]

    def __str__(self):
        return self.nome


class Lancamento(EmpresaModel, Rastreavel):
    TIPO_CHOICES = [("entrada", "Entrada"), ("saida", "Saída")]
    STATUS_CHOICES = [("previsto", "Previsto"), ("realizado", "Realizado")]

    conta = models.ForeignKey(ContaBancaria, on_delete=models.PROTECT, related_name="lancamentos")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name="lancamentos"
    )
    projeto = models.ForeignKey(
        Projeto, on_delete=models.SET_NULL, null=True, blank=True, related_name="lancamentos"
    )
    descricao = models.CharField(max_length=200, verbose_name="descrição")
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    data = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="realizado")

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "lançamento"
        verbose_name_plural = "lançamentos"

    def __str__(self):
        return f"{self.get_tipo_display()} R$ {self.valor} — {self.descricao}"
