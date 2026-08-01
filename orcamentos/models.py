from decimal import Decimal

from django.db import models

from core.models import EmpresaModel, Rastreavel
from projetos.models import Projeto


class Orcamento(EmpresaModel, Rastreavel):
    """Orçamento detalhado de execução do projeto — o custo da obra para o
    cliente, item a item. Não se confunde com a proposta, que é o honorário do
    escritório: a proposta cobra o projeto, o orçamento estima a execução.
    """

    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("enviado", "Enviado ao cliente"),
        ("aprovado", "Aprovado"),
        ("revisado", "Substituído por revisão"),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="orcamentos")
    titulo = models.CharField("título", max_length=200, default="Orçamento de execução")
    versao = models.CharField(
        "versão", max_length=20, default="1", help_text="Suba a versão a cada revisão enviada."
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="rascunho")
    bdi_percent = models.DecimalField(
        "BDI (%)",
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Benefícios e despesas indiretas aplicados sobre o custo dos itens.",
    )
    validade = models.DateField(null=True, blank=True)
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "orçamento"
        verbose_name_plural = "orçamentos"

    def __str__(self):
        return f"{self.titulo} v{self.versao} — {self.projeto.nome}"

    @property
    def custo_itens(self):
        return sum((item.total for item in self.itens.all()), Decimal("0"))

    @property
    def valor_bdi(self):
        return (self.custo_itens * self.bdi_percent / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def total(self):
        return self.custo_itens + self.valor_bdi

    @property
    def total_realizado(self):
        return sum((item.valor_realizado or Decimal("0") for item in self.itens.all()), Decimal("0"))

    @property
    def desvio(self):
        """Quanto o realizado passou do orçado, em reais. Negativo é economia."""
        realizados = [i for i in self.itens.all() if i.valor_realizado is not None]
        if not realizados:
            return None
        orcado = sum((i.total for i in realizados), Decimal("0"))
        return sum((i.valor_realizado for i in realizados), Decimal("0")) - orcado

    def por_categoria(self):
        """Soma por categoria, para o resumo do orçamento."""
        acumulado = {}
        for item in self.itens.select_related("fornecedor"):
            entrada = acumulado.setdefault(
                item.categoria,
                {"rotulo": item.get_categoria_display(), "total": Decimal("0"), "itens": 0},
            )
            entrada["total"] += item.total
            entrada["itens"] += 1
        return sorted(acumulado.values(), key=lambda e: e["total"], reverse=True)


class ItemOrcamento(EmpresaModel):
    CATEGORIA_CHOICES = [
        ("demolicao", "Demolição e remoção"),
        ("alvenaria", "Alvenaria e estrutura"),
        ("instalacoes", "Instalações"),
        ("revestimento", "Revestimentos"),
        ("marcenaria", "Marcenaria"),
        ("serralheria", "Serralheria e vidros"),
        ("pintura", "Pintura"),
        ("iluminacao", "Iluminação"),
        ("mobiliario", "Mobiliário e decoração"),
        ("paisagismo", "Paisagismo"),
        ("mao_de_obra", "Mão de obra"),
        ("taxas", "Taxas e aprovações"),
        ("outro", "Outro"),
    ]

    UNIDADE_CHOICES = [
        ("un", "un"),
        ("m", "m"),
        ("m2", "m²"),
        ("m3", "m³"),
        ("kg", "kg"),
        ("vb", "verba"),
        ("h", "h"),
        ("mes", "mês"),
    ]

    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name="itens")
    ambiente = models.CharField(
        max_length=120, blank=True, help_text="Ambiente ou frente de obra (ex.: cozinha)."
    )
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default="outro")
    descricao = models.CharField("descrição", max_length=250)
    unidade = models.CharField(max_length=5, choices=UNIDADE_CHOICES, default="un")
    quantidade = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    valor_unitario = models.DecimalField("valor unitário", max_digits=12, decimal_places=2, default=0)
    fornecedor = models.ForeignKey(
        "fornecedores.Fornecedor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="itens_orcamento",
    )
    valor_realizado = models.DecimalField(
        "valor realizado",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Preencha quando o item for efetivamente contratado ou pago.",
    )
    observacoes = models.CharField("observações", max_length=250, blank=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "id"]
        verbose_name = "item do orçamento"
        verbose_name_plural = "itens do orçamento"

    def __str__(self):
        return self.descricao

    @property
    def total(self):
        return (self.quantidade * self.valor_unitario).quantize(Decimal("0.01"))

    @property
    def desvio(self):
        if self.valor_realizado is None:
            return None
        return self.valor_realizado - self.total
