from django.db import models

from core.models import EmpresaModel


class Notificacao(EmpresaModel):
    NIVEL_CHOICES = [
        ("info", "Informação"),
        ("alerta", "Alerta"),
        ("critico", "Crítico"),
    ]

    titulo = models.CharField(max_length=160, verbose_name="título")
    mensagem = models.CharField(max_length=300, blank=True)
    nivel = models.CharField(max_length=10, choices=NIVEL_CHOICES, default="alerta")
    url = models.CharField(max_length=300, blank=True, help_text="Link relativo para a origem.")
    # Chave de deduplicação: evita recriar a mesma notificação a cada varredura.
    chave = models.CharField(max_length=120, blank=True)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["lida", "-criado_em"]
        verbose_name = "notificação"
        verbose_name_plural = "notificações"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "chave"],
                condition=models.Q(lida=False),
                name="notificacao_chave_unica_por_empresa",
            )
        ]

    def __str__(self):
        return self.titulo
