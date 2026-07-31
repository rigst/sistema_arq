from django.conf import settings
from django.db import models

from core.models import EmpresaModel, Rastreavel


class Cliente(EmpresaModel, Rastreavel):
    ORIGEM_CHOICES = [
        ("indicacao", "Indicação"),
        ("instagram", "Instagram"),
        ("site", "Site"),
        ("google", "Google"),
        ("evento", "Evento"),
        ("outro", "Outro"),
    ]
    FASE_CHOICES = [
        ("lead", "Lead"),
        ("contato", "Em contato"),
        ("proposta", "Proposta enviada"),
        ("negociacao", "Negociação"),
        ("ganho", "Fechado (ganho)"),
        ("perdido", "Perdido"),
    ]

    nome = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=40, blank=True)
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default="outro")
    fase = models.CharField(max_length=20, choices=FASE_CHOICES, default="lead")
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return self.nome


class Interacao(EmpresaModel):
    """Registro da timeline do cliente (conversas, reuniões, e-mails)."""

    TIPO_CHOICES = [
        ("nota", "Nota"),
        ("ligacao", "Ligação"),
        ("email", "E-mail"),
        ("reuniao", "Reunião"),
        ("whatsapp", "WhatsApp"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="interacoes")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="nota")
    descricao = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "interação"
        verbose_name_plural = "interações"

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.cliente.nome}"
