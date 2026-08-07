from django.conf import settings
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


class AvisoSistema(EmpresaModel):
    """O histórico dos avisos que passaram pelo canto da tela.

    O toast some em segundos, e às vezes some justo quando a pessoa desviou o
    olho. Guardar o que foi dito custa uma linha por ação e responde à pergunta
    que aparece dez minutos depois: "salvou mesmo? o que apareceu ali?".

    Não se confunde com Notificacao: aquela é gerada por varredura e diz o que
    PRECISA de atenção; esta é o registro do que ACONTECEU.
    """

    NIVEL_CHOICES = [
        ("sucesso", "Sucesso"),
        ("erro", "Erro"),
        ("atencao", "Atenção"),
    ]

    texto = models.CharField(max_length=300)
    nivel = models.CharField(max_length=10, choices=NIVEL_CHOICES, default="sucesso")
    # Onde aconteceu. "Tarefa criada." sozinho não diz nada três dias depois;
    # com o lugar e o link, o histórico responde "criada onde?" sem adivinhação.
    onde = models.CharField("onde", max_length=160, blank=True)
    url = models.CharField(max_length=300, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-id"]
        verbose_name = "aviso do sistema"
        verbose_name_plural = "avisos do sistema"

    def __str__(self):
        return self.texto

    @property
    def tem_destino(self):
        return bool(self.url)
