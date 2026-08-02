from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import EmpresaModel, Rastreavel
from crm.models import Cliente

# Etapas padrão por tipo (base NBR 13532). Usadas para instanciar as etapas de um
# projeto novo — templates editáveis por empresa ficam para fase futura.
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
        ("empresarial", "Empresarial"),
        ("institucional", "Institucional"),
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
    endereco = models.CharField("endereço", max_length=200, blank=True)
    cidade = models.CharField(max_length=120, blank=True)
    uf = models.CharField("UF", max_length=2, blank=True)
    cep = models.CharField("CEP", max_length=12, blank=True)
    area_terreno = models.DecimalField(
        "área do terreno (m²)", max_digits=10, decimal_places=2, null=True, blank=True
    )
    area_construida = models.DecimalField(
        "área construída prevista (m²)", max_digits=10, decimal_places=2, null=True, blank=True
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
    def fase_atual(self):
        """Onde o projeto está agora: a primeira fase aberta, ou a próxima a abrir."""
        abertas = self.fases.exclude(status="aprovada").order_by("ordem")
        return abertas.filter(status__in=["em_elaboracao", "aguardando_cliente", "ajustes"]).first() \
            or abertas.first()

    @property
    def localizacao(self):
        partes = [self.endereco, self.cidade]
        if self.uf:
            partes.append(self.uf.upper())
        return " · ".join(p for p in partes if p)

    @property
    def dias_parado(self):
        return (timezone.now() - self.ultima_atualizacao).days

    @property
    def lembretes_fixados(self):
        """Só os do projeto: os de fase se contam dentro da fase."""
        return self.lembretes.filter(fixado=True, fase__isnull=True).count()

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
