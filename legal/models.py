from django.conf import settings
from django.db import models
from django.utils import timezone


class DocumentoLegal(models.Model):
    """Um documento legal em uma versão específica.

    O aceite é registrado contra a versão, não contra o tipo: publicar uma
    versão nova faz o documento voltar a aparecer para todo mundo aceitar.
    """

    TERMOS = "termos"
    PRIVACIDADE = "privacidade"
    TIPO_CHOICES = [
        (TERMOS, "Termos de uso"),
        (PRIVACIDADE, "Política de privacidade"),
    ]

    tipo = models.CharField("tipo", max_length=20, choices=TIPO_CHOICES)
    versao = models.CharField(
        "versão", max_length=20, help_text="Ex.: 1.0. Uma versão nova exige aceite de todos."
    )
    titulo = models.CharField("título", max_length=160)
    resumo_mudancas = models.CharField(
        "resumo das mudanças",
        max_length=300,
        blank=True,
        help_text="O que mudou desde a versão anterior. Aparece na tela de aceite.",
    )
    conteudo = models.TextField(
        "conteúdo",
        help_text="Markdown simples: '## ' abre um título e linhas em branco separam parágrafos.",
    )
    vigente_desde = models.DateTimeField(
        "vigente desde",
        null=True,
        blank=True,
        help_text="Em branco, a versão fica como rascunho e não é exigida de ninguém.",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "documento legal"
        verbose_name_plural = "documentos legais"
        constraints = [
            models.UniqueConstraint(fields=["tipo", "versao"], name="documento_unico_por_versao"),
        ]
        ordering = ["tipo", "-vigente_desde", "-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} v{self.versao}"

    @property
    def url_publica(self):
        return "/termos/" if self.tipo == self.TERMOS else "/privacidade/"

    @property
    def paragrafos(self):
        """Quebra o conteúdo em blocos para o template, sem depender de
        biblioteca de markdown: ('titulo'|'texto'|'item', texto)."""
        blocos = []
        for trecho in self.conteudo.split("\n\n"):
            trecho = trecho.strip()
            if not trecho:
                continue
            if trecho.startswith("## "):
                blocos.append(("titulo", trecho[3:].strip()))
            elif trecho.startswith("- "):
                for linha in trecho.splitlines():
                    linha = linha.strip()
                    if linha.startswith("- "):
                        blocos.append(("item", linha[2:].strip()))
            else:
                blocos.append(("texto", " ".join(trecho.split())))
        return blocos


class AceiteLegal(models.Model):
    """Prova de que uma pessoa aceitou uma versão específica de um documento."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="aceites_legais",
        verbose_name="usuário",
    )
    documento = models.ForeignKey(
        DocumentoLegal, on_delete=models.PROTECT, related_name="aceites"
    )
    aceito_em = models.DateTimeField("aceito em", default=timezone.now)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("navegador", max_length=400, blank=True)

    class Meta:
        verbose_name = "aceite"
        verbose_name_plural = "aceites"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "documento"], name="aceite_unico_por_documento"
            ),
        ]
        ordering = ["-aceito_em"]

    def __str__(self):
        return f"{self.usuario} aceitou {self.documento} em {self.aceito_em:%d/%m/%Y %H:%M}"
