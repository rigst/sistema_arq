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
    orcamento_previsto = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, verbose_name="orçamento previsto"
    )
    prazo_desejado = models.DateField(null=True, blank=True, verbose_name="prazo desejado")
    # Bloco 4 — restrições do terreno / legais
    restricoes = models.TextField(
        blank=True,
        help_text="Recuos, gabarito, taxa de ocupação, infraestrutura.",
        verbose_name="restrições",
    )
    # Bloco 5 — referências e estilo
    referencias = models.TextField(
        blank=True, help_text="Links/observações de referências.", verbose_name="referências"
    )
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
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Área aproximada (m²).",
        verbose_name="área aproximada",
    )
    uso = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "ambiente do programa"
        verbose_name_plural = "programa de necessidades"

    def __str__(self):
        return self.nome

    @property
    def area_total(self):
        """Mantido por compatibilidade: cada ambiente é uma linha com a sua
        própria metragem, então total e unidade são a mesma coisa."""
        return self.area_aprox


# =====================================================================
# Templates de briefing — perguntas com respostas objetivas pré-prontas
# =====================================================================


class TemplateBriefing(EmpresaModel, Rastreavel):
    """Um roteiro de perguntas reaproveitável.

    O escritório monta o roteiro uma vez por tipo de projeto e, na reunião,
    só marca as opções. Isso é o que faz o briefing acontecer de verdade:
    escrever da estaca zero a cada cliente é o que ninguém faz.
    """

    nome = models.CharField(max_length=150)
    tipo_projeto = models.CharField(
        "tipo de projeto",
        max_length=20,
        blank=True,
        help_text="Deixe em branco para servir a qualquer tipo.",
    )
    descricao = models.TextField("descrição", blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "template de briefing"
        verbose_name_plural = "templates de briefing"

    def __str__(self):
        return self.nome


class PerguntaTemplate(EmpresaModel):
    TIPO_CHOICES = [
        ("opcao", "Escolha uma opção"),
        ("multipla", "Escolha várias"),
        ("texto", "Resposta escrita"),
        ("numero", "Número"),
    ]

    template = models.ForeignKey(
        TemplateBriefing, on_delete=models.CASCADE, related_name="perguntas"
    )
    bloco = models.CharField(
        max_length=80,
        blank=True,
        help_text="Agrupa as perguntas na tela (ex.: Rotina, Orçamento, Estilo).",
    )
    texto = models.CharField(max_length=300)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default="opcao")
    ajuda = models.CharField(max_length=250, blank=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "id"]
        verbose_name = "pergunta do template"
        verbose_name_plural = "perguntas do template"

    def __str__(self):
        return self.texto

    @property
    def aceita_opcoes(self):
        return self.tipo in {"opcao", "multipla"}


class OpcaoPergunta(EmpresaModel):
    """Resposta objetiva pré-pronta. É o que se marca na reunião."""

    pergunta = models.ForeignKey(PerguntaTemplate, on_delete=models.CASCADE, related_name="opcoes")
    texto = models.CharField(max_length=200)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "id"]
        verbose_name = "opção de resposta"
        verbose_name_plural = "opções de resposta"

    def __str__(self):
        return self.texto


class RespostaBriefing(EmpresaModel):
    """O que o cliente respondeu. Opções marcadas e o complemento escrito
    convivem: a opção dá a estrutura, o texto guarda o que só aquele cliente
    disse."""

    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name="respostas")
    pergunta = models.ForeignKey(
        PerguntaTemplate, on_delete=models.CASCADE, related_name="respostas"
    )
    opcoes = models.ManyToManyField(OpcaoPergunta, blank=True, related_name="respostas")
    texto = models.TextField("complemento", blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["briefing", "pergunta"], name="resposta_unica_por_pergunta"
            )
        ]
        ordering = ["pergunta__ordem", "id"]
        verbose_name = "resposta do briefing"
        verbose_name_plural = "respostas do briefing"

    def __str__(self):
        return f"{self.pergunta} — {self.resumo}"

    @property
    def resumo(self):
        """Opções marcadas e complemento em uma linha, para leitura e para a IA."""
        partes = [o.texto for o in self.opcoes.all()]
        if self.texto.strip():
            partes.append(self.texto.strip())
        return " · ".join(partes)
