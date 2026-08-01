from django.conf import settings
from django.db import models

from core.models import EmpresaModel, Rastreavel
from projetos.models import Projeto


class Contrato(EmpresaModel, Rastreavel):
    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("ativo", "Ativo (assinado)"),
        ("encerrado", "Encerrado"),
        ("cancelado", "Cancelado"),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="contratos")
    numero = models.CharField(max_length=40, blank=True, verbose_name="número")
    titulo = models.CharField(max_length=200, verbose_name="título")
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="valor total")
    data_assinatura = models.DateField(null=True, blank=True, verbose_name="data de assinatura")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="rascunho")
    observacoes = models.TextField(blank=True, verbose_name="observações")
    # Evita lançar as parcelas mais de uma vez no financeiro.
    parcelas_lancadas = models.BooleanField(default=False, verbose_name="parcelas lançadas")

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "contrato"
        verbose_name_plural = "contratos"

    def __str__(self):
        return self.titulo

    @property
    def cliente(self):
        return self.projeto.cliente


class Parcela(EmpresaModel):
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="parcelas")
    numero = models.PositiveIntegerField(default=1, verbose_name="número")
    descricao = models.CharField(max_length=120, blank=True, verbose_name="descrição")
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    vencimento = models.DateField()
    paga = models.BooleanField(default=False)
    # Lançamento (contas a receber) gerado no financeiro.
    lancamento = models.ForeignKey(
        "financeiro.Lancamento", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["vencimento", "numero"]
        verbose_name = "parcela"
        verbose_name_plural = "parcelas"

    def __str__(self):
        return f"Parcela {self.numero} — R$ {self.valor}"


class AlteracaoEscopo(EmpresaModel):
    """Registro append-only de alterações de escopo/aditivos por contrato."""

    TIPO_CHOICES = [
        ("aditivo", "Aditivo (novo escopo)"),
        ("alteracao", "Alteração de escopo"),
        ("aprovacao", "Aprovação registrada"),
    ]

    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="alteracoes")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="alteracao")
    descricao = models.TextField( verbose_name="descrição")
    valor_delta = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Impacto no valor (+/-).",
        verbose_name="variação de valor",
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "alteração de escopo"
        verbose_name_plural = "alterações de escopo"

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.contrato.titulo}"


class Documento(EmpresaModel):
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE, related_name="documentos", null=True, blank=True
    )
    contrato = models.ForeignKey(
        Contrato, on_delete=models.CASCADE, related_name="documentos", null=True, blank=True
    )
    titulo = models.CharField(max_length=200, verbose_name="título")
    arquivo = models.FileField(upload_to="documentos/%Y/%m/")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.titulo
