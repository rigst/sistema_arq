from django.db import models

from core.models import EmpresaModel, Rastreavel
from projetos.models import Projeto


class Arquivo(EmpresaModel, Rastreavel):
    """Tudo que entra e sai do projeto em forma de arquivo.

    Três eixos independentes respondem às perguntas que o escritório faz:
    `fluxo` diz de onde veio ou para onde foi, `categoria` diz o que é, e
    `status` diz em que pé está — inclusive se já foi pago.
    """

    FLUXO_CHOICES = [
        ("enviado_cliente", "Enviado ao cliente"),
        ("recebido_cliente", "Recebido do cliente"),
        ("enviado_fornecedor", "Enviado ao fornecedor"),
        ("recebido_fornecedor", "Recebido do fornecedor"),
        ("orgao", "Órgão público / concessionária"),
        ("interno", "Interno do escritório"),
    ]

    CATEGORIA_CHOICES = [
        ("projeto", "Prancha / projeto"),
        ("memorial", "Memorial e especificação"),
        ("proposta", "Proposta"),
        ("contrato", "Contrato e aditivo"),
        ("orcamento", "Orçamento"),
        ("nota", "Nota fiscal"),
        ("recibo", "Recibo / comprovante"),
        ("licenca", "Licença e aprovação"),
        ("levantamento", "Levantamento e medição"),
        ("foto", "Foto de obra"),
        ("referencia", "Referência e imagem"),
        ("outro", "Outro"),
    ]

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("enviado", "Enviado"),
        ("aprovado", "Aprovado"),
        ("pago", "Pago"),
        ("recusado", "Recusado"),
    ]

    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE, related_name="arquivos", null=True, blank=True
    )
    fornecedor = models.ForeignKey(
        "fornecedores.Fornecedor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="arquivos",
    )
    titulo = models.CharField("título", max_length=200)
    arquivo = models.FileField(upload_to="arquivos/%Y/%m/")
    fluxo = models.CharField(max_length=25, choices=FLUXO_CHOICES, default="interno")
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default="outro")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    data = models.DateField("data de referência", null=True, blank=True)
    valor = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Só para nota, recibo ou orçamento — deixa o financeiro rastreável.",
    )
    lancamento = models.ForeignKey(
        "financeiro.Lancamento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Lançamento gerado no financeiro, quando houver.",
    )
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "arquivo"
        verbose_name_plural = "arquivos"

    def __str__(self):
        return self.titulo

    @property
    def extensao(self):
        nome = self.arquivo.name or ""
        return nome.rsplit(".", 1)[-1].lower() if "." in nome else ""

    @property
    def eh_financeiro(self):
        return self.categoria in {"nota", "recibo", "orcamento"} and self.valor is not None
