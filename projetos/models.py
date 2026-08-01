from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import EmpresaModel, Rastreavel
from crm.models import Cliente

# Etapas padrão por tipo (base NBR 13532). Usadas para instanciar as etapas de um
# projeto novo — templates editáveis por empresa ficam para fase futura.
# Só a fase de projeto. O acompanhamento de obra saiu daqui: nem todo trabalho
# tem execução, e criar a etapa para todo mundo fazia o cronograma nascer com
# uma linha que nunca ia ser cumprida. Quando o projeto tem execução, ela vira
# uma Obra de verdade, com etapas construtivas próprias.
ETAPAS_PADRAO = {
    "residencial": ["Levantamento", "Estudo preliminar", "Anteprojeto", "Projeto legal", "Projeto executivo"],
    "comercial": ["Levantamento", "Estudo preliminar", "Anteprojeto", "Projeto legal", "Projeto executivo"],
    "corporativo": ["Briefing", "Estudo preliminar", "Anteprojeto", "Detalhamento", "Executivo"],
    "interiores": ["Briefing", "Conceito", "Layout", "Detalhamento", "Executivo de interiores"],
}


class Tag(EmpresaModel):
    nome = models.CharField(max_length=40)
    cor = models.CharField(max_length=7, blank=True, default="#2563eb")

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Projeto(EmpresaModel, Rastreavel):
    TIPO_CHOICES = [
        ("residencial", "Residencial"),
        ("comercial", "Comercial"),
        ("corporativo", "Corporativo"),
        ("interiores", "Interiores"),
    ]
    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("pausado", "Pausado"),
        ("concluido", "Concluído"),
        ("cancelado", "Cancelado"),
    ]

    nome = models.CharField(max_length=150)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="projetos")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="residencial")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ativo")
    tem_execucao = models.BooleanField(
        "acompanha a execução",
        default=False,
        help_text="Marque se o escritório também acompanha a obra. Muitos trabalhos "
                  "terminam no projeto entregue.",
    )
    valor_contratado = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="valor contratado")
    horas_estimadas = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Horas previstas (vindas da proposta). Comparadas com as trabalhadas.",
        verbose_name="horas estimadas",
    )
    data_inicio = models.DateField(null=True, blank=True, verbose_name="data de início")
    data_prevista = models.DateField(null=True, blank=True, verbose_name="data prevista")
    ultima_atualizacao = models.DateTimeField(default=timezone.now, verbose_name="última atualização")
    tags = models.ManyToManyField(Tag, blank=True, related_name="projetos")

    class Meta:
        ordering = ["-ultima_atualizacao"]
        verbose_name = "projeto"
        verbose_name_plural = "projetos"

    def __str__(self):
        return self.nome

    def tocar(self):
        """Marca a última atualização (chamado quando algo do projeto muda)."""
        self.ultima_atualizacao = timezone.now()
        self.save(update_fields=["ultima_atualizacao"])

    @property
    def etapa_atual(self):
        return self.etapas.filter(status="andamento").order_by("ordem").first() or \
            self.etapas.exclude(status="concluida").order_by("ordem").first()

    @property
    def dias_parado(self):
        return (timezone.now() - self.ultima_atualizacao).days

    @property
    def pendencias_abertas(self):
        return self.pendencias.filter(resolvida=False).count()

    @property
    def horas_trabalhadas(self):
        from decimal import Decimal

        total = Decimal("0")
        for ap in self.apontamentos.all():
            total += ap.horas
        return total.quantize(Decimal("0.01"))

    @property
    def horas_saldo(self):
        """Horas estimadas − trabalhadas. Negativo = estourou a estimativa."""
        return (self.horas_estimadas or 0) - self.horas_trabalhadas


class Etapa(EmpresaModel):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("andamento", "Em andamento"),
        ("concluida", "Concluída"),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="etapas")
    nome = models.CharField(max_length=100)
    ordem = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    data_prevista = models.DateField(null=True, blank=True, verbose_name="data prevista")
    fornecedor = models.ForeignKey(
        "fornecedores.Fornecedor",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="etapas_projeto",
        help_text="Quem executa esta etapa, quando é terceirizada.",
    )
    aprovada = models.BooleanField(default=False)
    aprovada_em = models.DateTimeField(null=True, blank=True, verbose_name="aprovada em")

    class Meta:
        ordering = ["ordem", "id"]

    def __str__(self):
        return f"{self.projeto.nome} — {self.nome}"


class Pendencia(EmpresaModel):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="pendencias")
    descricao = models.CharField(max_length=200, verbose_name="descrição")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        verbose_name="responsável",
    )
    prazo = models.DateField(null=True, blank=True)
    resolvida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["resolvida", "prazo"]

    def __str__(self):
        return self.descricao


class Disciplina(EmpresaModel):
    """Um projeto de arquitetura é vários projetos.

    Arquitetônico, estrutural, hidráulico, elétrico — cada um com seu prazo e,
    muitas vezes, seu projetista de fora. Tratar tudo como "o projeto" esconde
    justamente onde as coisas travam: o arquitetônico está pronto e o estrutural
    nem começou.
    """

    NOME_CHOICES = [
        ("arquitetonico", "Arquitetônico"),
        ("estrutural", "Estrutural"),
        ("hidraulico", "Hidrossanitário"),
        ("eletrico", "Elétrico"),
        ("climatizacao", "Climatização"),
        ("incendio", "Prevenção de incêndio"),
        ("luminotecnico", "Luminotécnico"),
        ("paisagismo", "Paisagismo"),
        ("interiores", "Interiores"),
        ("marcenaria", "Detalhamento de marcenaria"),
        ("outro", "Outro"),
    ]
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("andamento", "Em andamento"),
        ("concluida", "Concluída"),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="disciplinas")
    nome = models.CharField(max_length=20, choices=NOME_CHOICES, default="arquitetonico")
    descricao = models.CharField("descrição", max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    interna = models.BooleanField(
        "feita pelo escritório", default=True,
        help_text="Desmarque quando um projetista de fora assina esta disciplina.",
    )
    fornecedor = models.ForeignKey(
        "fornecedores.Fornecedor",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="disciplinas",
        verbose_name="projetista externo",
    )
    prazo = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "disciplina"
        verbose_name_plural = "disciplinas"
        constraints = [
            models.UniqueConstraint(fields=["projeto", "nome"], name="disciplina_unica_por_projeto")
        ]

    def __str__(self):
        return f"{self.projeto.nome} — {self.get_nome_display()}"

    @property
    def responsavel_visivel(self):
        if self.interna:
            return "escritório"
        return self.fornecedor.nome if self.fornecedor_id else "a definir"


def criar_etapas_padrao(projeto):
    nomes = ETAPAS_PADRAO.get(projeto.tipo, ETAPAS_PADRAO["residencial"])
    Etapa.objects.bulk_create(
        [
            Etapa(empresa=projeto.empresa, projeto=projeto, nome=nome, ordem=i)
            for i, nome in enumerate(nomes)
        ]
    )
