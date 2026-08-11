from django.conf import settings
from django.db import models

from core.models import EmpresaModel, Rastreavel
from core.uploads import validar_documento
from projetos.models import Projeto


class Contrato(EmpresaModel, Rastreavel):
    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("enviado", "Enviado ao cliente"),
        ("ajustes", "Em alterações"),
        ("aprovado", "Aprovado"),
        ("ativo", "Ativo (assinado)"),
        ("encerrado", "Encerrado"),
        ("cancelado", "Cancelado"),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="contratos")
    numero = models.CharField(max_length=40, blank=True, verbose_name="número")
    titulo = models.CharField(max_length=200, verbose_name="título")
    valor_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="valor total"
    )
    data_assinatura = models.DateField(null=True, blank=True, verbose_name="data de assinatura")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="rascunho")
    observacoes = models.TextField(blank=True, verbose_name="observações")
    corpo = models.TextField(
        "texto do contrato",
        blank=True,
        help_text="Cláusulas do contrato. Gere a partir de um modelo e revise aqui.",
    )
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

    @property
    def editavel(self):
        """Um documento enviado só volta a mudar após uma decisão explícita."""
        return self.status in {"rascunho", "ajustes"}

    @property
    def pronto_para_envio(self):
        return bool(self.corpo.strip()) and self.valor_total > 0

    @property
    def assinado(self):
        """A data registrada é o marco que libera a operação financeira."""
        return self.data_assinatura is not None


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
        ("alteracao", "Alteração de escopo"),
        ("aditivo", "Aditivo contratual"),
        ("prazo", "Alteração de prazo"),
        ("condicoes", "Condições contratuais"),
        ("aprovacao", "Aprovação registrada"),
    ]

    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="alteracoes")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="alteracao")
    descricao = models.TextField(verbose_name="descrição")
    valor_delta = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Impacto no valor (+/-).",
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
    arquivo = models.FileField(upload_to="documentos/%Y/%m/", validators=[validar_documento])
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.titulo

    @property
    def nome_arquivo(self):
        from pathlib import Path

        # `or ""` porque FileField.name é None enquanto nenhum arquivo foi
        # atribuído — e Path(None) levanta TypeError em vez de devolver vazio.
        return Path(self.arquivo.name or "").name

    @property
    def extensao(self):
        from pathlib import Path

        return Path(self.arquivo.name or "").suffix.removeprefix(".").upper() or "ARQ"


class ModeloContrato(EmpresaModel, Rastreavel):
    """Minuta reaproveitável. O corpo usa marcadores entre chaves duplas que
    são trocados pelos dados do projeto na hora de gerar — assim o escritório
    escreve o contrato uma vez e só confere nas próximas."""

    MARCADORES = {
        "{{cliente}}": "Nome do cliente",
        "{{cliente_documento}}": "CPF/CNPJ do cliente",
        "{{cliente_email}}": "E-mail do cliente",
        "{{cliente_telefone}}": "Telefone do cliente",
        "{{projeto}}": "Nome do projeto",
        "{{tipo_projeto}}": "Tipo do projeto",
        "{{escritorio}}": "Nome do escritório",
        "{{valor}}": "Valor total do contrato",
        "{{horas}}": "Horas previstas",
        "{{data}}": "Data de hoje",
        "{{data_inicio}}": "Data prevista de início",
        "{{prazo}}": "Data prevista de entrega",
        "{{cronograma}}": "Prazos em dias úteis por fase",
        "{{escopo}}": "Itens e valores da proposta",
        "{{endereco}}": "Endereço da obra",
        "{{area_terreno}}": "Área do terreno",
        "{{area_construida}}": "Área construída prevista",
    }

    nome = models.CharField(max_length=150)
    tipo_projeto = models.CharField(
        "tipo de projeto",
        max_length=20,
        blank=True,
        choices=Projeto.TIPO_CHOICES,
        help_text="Deixe em branco para servir a qualquer tipo de projeto.",
    )
    descricao = models.CharField("descrição", max_length=250, blank=True)
    corpo = models.TextField(
        help_text="Use marcadores como {{cliente}} e {{valor}}; eles são trocados ao gerar."
    )
    padrao = models.BooleanField(
        "modelo padrão", default=False, help_text="Sugerido primeiro ao criar um contrato."
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-padrao", "nome"]
        verbose_name = "modelo de contrato"
        verbose_name_plural = "modelos de contrato"

    def __str__(self):
        return self.nome

    def gerar(self, contexto: dict) -> str:
        """Troca os marcadores pelos valores. O que não vier no contexto fica
        visível como [PREENCHER: ...] em vez de sumir silenciosamente."""
        texto = self.corpo
        for marcador, rotulo in self.MARCADORES.items():
            chave = marcador.strip("{}")
            valor = contexto.get(chave)
            texto = texto.replace(marcador, str(valor) if valor else f"[PREENCHER: {rotulo}]")
        return texto
