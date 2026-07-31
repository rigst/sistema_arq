from django.db import models

from core.models import EmpresaModel, Rastreavel
from projetos.models import Projeto


class Briefing(EmpresaModel, Rastreavel):
    """Briefing estruturado (base NBR 13532), vinculado ao projeto e acessível
    durante toda a obra. Cinco blocos + programa de necessidades (ambientes)."""

    projeto = models.OneToOneField(Projeto, on_delete=models.CASCADE, related_name="briefing")

    # Bloco 1 — perfil e rotina do usuário
    perfil_usuarios = models.TextField(
        blank=True, help_text="Quem ocupa o espaço e a rotina do dia a dia."
    )
    # Bloco 3 — orçamento e prazo
    orcamento_previsto = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    prazo_desejado = models.DateField(null=True, blank=True)
    # Bloco 4 — restrições do terreno / legais
    restricoes = models.TextField(
        blank=True, help_text="Recuos, gabarito, taxa de ocupação, infraestrutura."
    )
    # Bloco 5 — referências e estilo
    referencias = models.TextField(blank=True, help_text="Links/observações de referências.")
    estilo = models.CharField(max_length=200, blank=True, help_text="Prioridades estéticas.")

    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "briefing"
        verbose_name_plural = "briefings"

    def __str__(self):
        return f"Briefing — {self.projeto.nome}"


class AmbientePrograma(EmpresaModel):
    """Bloco 2 — programa de necessidades: um ambiente do projeto."""

    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name="ambientes")
    nome = models.CharField(max_length=100)
    area_aprox = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, help_text="Área aproximada (m²)."
    )
    uso = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "ambiente do programa"
        verbose_name_plural = "programa de necessidades"

    def __str__(self):
        return self.nome
