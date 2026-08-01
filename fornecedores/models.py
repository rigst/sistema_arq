from django.db import models

from core.models import EmpresaModel, Rastreavel


class Fornecedor(EmpresaModel, Rastreavel):
    """Quem executa ou fornece — marcenaria, serralheria, elétrica, mobiliário.

    O cadastro alimenta o orçamento: cada item pode apontar para o fornecedor
    que deu o preço, e a avaliação registra como foi trabalhar com ele.
    """

    CATEGORIA_CHOICES = [
        ("marcenaria", "Marcenaria"),
        ("serralheria", "Serralheria"),
        ("marmoraria", "Marmoraria"),
        ("vidracaria", "Vidraçaria"),
        ("eletrica", "Elétrica"),
        ("hidraulica", "Hidráulica"),
        ("climatizacao", "Climatização"),
        ("gesso", "Gesso e forro"),
        ("pintura", "Pintura"),
        ("piso", "Piso e revestimento"),
        ("iluminacao", "Iluminação"),
        ("mobiliario", "Mobiliário e decoração"),
        ("paisagismo", "Paisagismo"),
        ("obra_civil", "Obra civil"),
        ("projeto", "Projeto complementar"),
        ("outro", "Outro"),
    ]

    nome = models.CharField(max_length=150)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default="outro")
    contato = models.CharField("pessoa de contato", max_length=150, blank=True)
    telefone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    site = models.URLField(blank=True)
    documento = models.CharField(
        "CNPJ/CPF", max_length=30, blank=True, help_text="Só para emissão de nota."
    )
    cidade = models.CharField(max_length=120, blank=True)
    prazo_medio_dias = models.PositiveIntegerField(
        "prazo médio (dias)", null=True, blank=True, help_text="Da aprovação à entrega."
    )
    avaliacao = models.PositiveSmallIntegerField(
        "avaliação",
        null=True,
        blank=True,
        choices=[(n, "★" * n) for n in range(1, 6)],
        help_text="Como foi trabalhar com ele da última vez.",
    )
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "fornecedor"
        verbose_name_plural = "fornecedores"

    def __str__(self):
        return self.nome

    @property
    def total_orcado(self):
        """Quanto já foi orçado com este fornecedor, somando todos os itens."""
        from decimal import Decimal

        return sum((item.total for item in self.itens_orcamento.all()), Decimal("0"))
