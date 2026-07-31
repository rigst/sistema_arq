from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import EmpresaModel, Rastreavel
from projetos.models import Projeto

# Etapas de obra padrão (base construtiva). Instanciadas ao abrir a obra.
ETAPAS_OBRA_PADRAO = [
    "Serviços preliminares",
    "Fundação",
    "Estrutura",
    "Alvenaria",
    "Instalações",
    "Acabamento",
]

# Desvio (previsto − real, em pontos percentuais) a partir do qual a obra é sinalizada.
LIMITE_DESVIO_PP = Decimal("8")


class Obra(EmpresaModel, Rastreavel):
    STATUS_CHOICES = [
        ("planejada", "Planejada"),
        ("andamento", "Em andamento"),
        ("paralisada", "Paralisada"),
        ("concluida", "Concluída"),
    ]

    projeto = models.OneToOneField(Projeto, on_delete=models.CASCADE, related_name="obra")
    endereco = models.CharField(max_length=250, blank=True)
    responsavel_tecnico = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planejada")
    data_inicio = models.DateField(null=True, blank=True)
    data_prevista_fim = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "obra"
        verbose_name_plural = "obras"

    def __str__(self):
        return f"Obra — {self.projeto.nome}"

    @property
    def cliente(self):
        return self.projeto.cliente

    def _avanco(self, campo):
        """Avanço ponderado pelo valor de cada etapa (média simples se sem valores)."""
        etapas = list(self.etapas.all())
        if not etapas:
            return Decimal("0")
        total_peso = sum((e.valor or Decimal("0")) for e in etapas)
        if total_peso > 0:
            soma = sum((e.valor or Decimal("0")) * getattr(e, campo) for e in etapas)
            return (soma / total_peso).quantize(Decimal("0.1"))
        soma = sum(getattr(e, campo) for e in etapas)
        return (soma / len(etapas)).quantize(Decimal("0.1"))

    @property
    def avanco_previsto(self):
        return self._avanco("percentual_previsto")

    @property
    def avanco_real(self):
        return self._avanco("percentual_real")

    @property
    def desvio(self):
        """Pontos percentuais atrasados (previsto − real). Positivo = obra atrasada."""
        return (self.avanco_previsto - self.avanco_real).quantize(Decimal("0.1"))

    @property
    def em_desvio(self):
        return self.desvio >= LIMITE_DESVIO_PP

    @property
    def pendencias_visitas(self):
        return self.visitas.exclude(pendencias="").count()


class EtapaObra(EmpresaModel):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="etapas")
    nome = models.CharField(max_length=120)
    ordem = models.PositiveIntegerField(default=0)
    data_prevista_inicio = models.DateField(null=True, blank=True)
    data_prevista_fim = models.DateField(null=True, blank=True)
    percentual_previsto = models.DecimalField(
        max_digits=5, decimal_places=1, default=0, help_text="Avanço planejado até hoje (0–100)."
    )
    percentual_real = models.DecimalField(
        max_digits=5, decimal_places=1, default=0, help_text="Avanço executado (0–100)."
    )
    valor = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text="Valor da etapa; base da medição e do peso no cronograma.",
    )

    class Meta:
        ordering = ["ordem", "id"]
        verbose_name = "etapa de obra"
        verbose_name_plural = "etapas de obra"

    def __str__(self):
        return f"{self.obra.projeto.nome} — {self.nome}"

    @property
    def desvio(self):
        return (Decimal(self.percentual_previsto) - Decimal(self.percentual_real)).quantize(
            Decimal("0.1")
        )

    @property
    def em_desvio(self):
        return self.desvio >= LIMITE_DESVIO_PP

    @property
    def valor_medido(self):
        """Soma das medições aprovadas desta etapa."""
        total = sum((m.valor_liberado for m in self.medicoes.filter(aprovada=True)), Decimal("0"))
        return total.quantize(Decimal("0.01"))


class VisitaTecnica(EmpresaModel, Rastreavel):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="visitas")
    etapa = models.ForeignKey(
        EtapaObra, on_delete=models.SET_NULL, null=True, blank=True, related_name="visitas"
    )
    data = models.DateField(default=timezone.localdate)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    verificado = models.TextField(help_text="O que foi verificado na visita.")
    pendencias = models.TextField(blank=True, help_text="Pendências a resolver (deixe vazio se ok).")
    proxima_acao = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "visita técnica"
        verbose_name_plural = "visitas técnicas"

    def __str__(self):
        return f"Visita {self.data:%d/%m/%Y} — {self.obra.projeto.nome}"


class Medicao(EmpresaModel):
    etapa = models.ForeignKey(EtapaObra, on_delete=models.CASCADE, related_name="medicoes")
    data = models.DateField(default=timezone.localdate)
    percentual_medido = models.DecimalField(
        max_digits=5, decimal_places=1, default=0, help_text="Avanço verificado nesta medição."
    )
    valor_liberado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descricao = models.CharField(max_length=200, blank=True)
    aprovada = models.BooleanField(default=False)
    # Lançamento (contas a receber) criado no financeiro ao aprovar.
    lancamento = models.ForeignKey(
        "financeiro.Lancamento", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "medição"
        verbose_name_plural = "medições"

    def __str__(self):
        return f"Medição {self.percentual_medido}% — {self.etapa.nome}"


def criar_etapas_obra_padrao(obra):
    EtapaObra.objects.bulk_create(
        [
            EtapaObra(empresa=obra.empresa, obra=obra, nome=nome, ordem=i)
            for i, nome in enumerate(ETAPAS_OBRA_PADRAO)
        ]
    )
