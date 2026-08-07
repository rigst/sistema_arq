from django.db import models

from core.models import EmpresaModel, Rastreavel
from crm.models import Cliente
from projetos.models import Projeto


class Compromisso(EmpresaModel, Rastreavel):
    # Os tipos seguem o fluxo do projeto: quase todo compromisso de escritório
    # de arquitetura é uma etapa acontecendo, não um evento genérico.
    TIPO_CHOICES = [
        ("briefing", "Reunião de briefing"),
        ("levantamento", "Levantamento em campo"),
        ("apresentacao", "Apresentação ao cliente"),
        ("reuniao", "Reunião"),
        ("assinatura", "Assinatura de contrato"),
        ("entrega", "Entrega de fase"),
        ("orgao", "Protocolo ou órgão público"),
        ("visita", "Visita a obra"),
        ("medicao", "Medição de obra"),
        ("prazo", "Prazo/entrega"),
        ("outro", "Outro"),
    ]

    titulo = models.CharField(max_length=200, verbose_name="título")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="reuniao")
    inicio = models.DateTimeField(verbose_name="início")
    fim = models.DateTimeField(null=True, blank=True)
    local = models.CharField(max_length=200, blank=True)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="compromissos"
    )
    projeto = models.ForeignKey(
        Projeto, on_delete=models.SET_NULL, null=True, blank=True, related_name="compromissos"
    )
    observacoes = models.TextField(blank=True, verbose_name="observações")

    class Meta:
        ordering = ["inicio"]
        verbose_name = "compromisso"
        verbose_name_plural = "compromissos"

    def __str__(self):
        return f"{self.titulo} — {self.inicio:%d/%m %H:%M}"
