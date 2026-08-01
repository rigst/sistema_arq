from django.conf import settings
from django.db import models


class Empresa(models.Model):
    """Tenant do sistema. Cada escritório é uma Empresa vinculada a um auth.Group;
    todas as entidades de negócio filtram por esse grupo."""

    nome = models.CharField(max_length=150, unique=True)
    grupo = models.OneToOneField(
        "auth.Group",
        on_delete=models.PROTECT,
        related_name="empresa_registro",
    )
    ativa = models.BooleanField(default=True)
    # Identidade visual do escritório: aparece no painel e nos documentos.
    logo = models.ImageField(upload_to="empresas/logos/", blank=True, null=True)
    imagem_fundo = models.ImageField(
        "imagem de fundo",
        upload_to="empresas/fundos/",
        blank=True,
        null=True,
        help_text="Foto larga que abre o painel. Sem ela, entra a imagem padrão.",
    )
    cor_primaria = models.CharField(max_length=7, blank=True, default="", verbose_name="cor primária")
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "empresa"
        verbose_name_plural = "empresas"

    def __str__(self):
        return self.nome


class EmpresaModel(models.Model):
    """Base para toda entidade de negócio: vincula ao tenant (grupo da empresa).
    O CASCADE garante que, ao remover o grupo de um visitante, os dados vão junto
    (a limpeza explícita em core.visitante_cleanup continua sendo a via principal)."""

    empresa = models.ForeignKey(
        "auth.Group",
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name="empresa",
    )

    class Meta:
        abstract = True


class Rastreavel(models.Model):
    """Mixin com o 'selo de origem' e trilha de criação. Toda entidade de negócio
    deve herdar deste mixin para suportar a rastreabilidade da jornada do dado
    (Briefing → Orçamento → Proposta → Contrato → Projeto → Obra → Financeiro)."""

    origem_tipo = models.CharField(max_length=50, blank=True, default="")
    origem_id = models.PositiveBigIntegerField(null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
