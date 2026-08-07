from django.db import models
from django.utils import timezone

from core.models import EmpresaModel, Rastreavel
from core.uploads import validar_documento
from projetos.models import Projeto

# Dias antes do vencimento em que a obrigação passa a "vencendo".
JANELA_ALERTA_DIAS = 30


class ObrigacaoTecnica(EmpresaModel, Rastreavel):
    """Registro de conformidade profissional: ART (CREA), RRT (CAU) ou vínculo CAU."""

    TIPO_CHOICES = [
        ("art", "ART (CREA)"),
        ("rrt", "RRT (CAU)"),
        ("cau", "Registro/vínculo CAU"),
    ]
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("registrada", "Registrada"),
        ("baixada", "Baixada"),
    ]

    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name="obrigacoes",
        null=True,
        blank=True,
        help_text="Deixe vazio para obrigações do escritório (ex.: registro CAU).",
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default="art")
    numero = models.CharField(max_length=60, blank=True, verbose_name="número")
    responsavel_tecnico = models.CharField(
        max_length=150, blank=True, verbose_name="responsável técnico"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    data_registro = models.DateField(null=True, blank=True, verbose_name="data de registro")
    vencimento = models.DateField(null=True, blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    arquivo = models.FileField(
        upload_to="regulatorio/%Y/%m/", null=True, blank=True, validators=[validar_documento]
    )
    observacoes = models.TextField(blank=True, verbose_name="observações")

    class Meta:
        ordering = ["status", "vencimento", "-criado_em"]
        verbose_name = "obrigação técnica"
        verbose_name_plural = "obrigações técnicas"

    def __str__(self):
        return f"{self.get_tipo_display()} {self.numero}".strip()

    @property
    def vencida(self):
        return bool(
            self.vencimento and self.status != "baixada" and self.vencimento < timezone.localdate()
        )

    @property
    def dias_para_vencer(self):
        if not self.vencimento:
            return None
        return (self.vencimento - timezone.localdate()).days

    @property
    def vencendo(self):
        dias = self.dias_para_vencer
        return bool(
            dias is not None and self.status != "baixada" and 0 <= dias <= JANELA_ALERTA_DIAS
        )

    @property
    def pendente_registro(self):
        return self.status == "pendente"
