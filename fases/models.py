from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import EmpresaModel, Rastreavel
from projetos.models import Projeto

from . import catalogo


class Fase(EmpresaModel, Rastreavel):
    """Uma fase do projeto, com seu próprio material e sua própria aprovação.

    O ponto da fase não é marcar progresso: é ser o lugar onde mora tudo daquela
    etapa — arquivos, conversa com o cliente, o parecer que autorizou seguir.
    Sem isso, o executivo e o estudo preliminar acabam na mesma pasta e ninguém
    sabe qual versão o cliente aprovou.
    """

    NAO_INICIADA = "nao_iniciada"
    EM_ELABORACAO = "em_elaboracao"
    AGUARDANDO = "aguardando_cliente"
    AJUSTES = "ajustes"
    APROVADA = "aprovada"

    STATUS_CHOICES = [
        (NAO_INICIADA, "Não iniciada"),
        (EM_ELABORACAO, "Em elaboração"),
        (AGUARDANDO, "Enviada ao cliente"),
        (AJUSTES, "Ajustes pedidos"),
        (APROVADA, "Aprovada"),
    ]
    ABERTAS = (EM_ELABORACAO, AGUARDANDO, AJUSTES)

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="fases")
    chave = models.CharField(max_length=30, choices=catalogo.CHOICES)
    ordem = models.PositiveIntegerField(default=0)
    titulo_livre = models.CharField(
        "nome do complementar", max_length=120, blank=True,
        help_text="Só para complementar fora da lista — acústico, automação, luminotécnico.",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NAO_INICIADA)

    prazo = models.DateField(null=True, blank=True, help_text="Data combinada de entrega.")
    iniciada_em = models.DateTimeField(null=True, blank=True, verbose_name="iniciada em")
    enviada_em = models.DateTimeField(null=True, blank=True, verbose_name="enviada em")
    respondida_em = models.DateTimeField(null=True, blank=True, verbose_name="respondida em")
    parecer = models.TextField(
        blank=True, help_text="O que o cliente respondeu ao aprovar ou pedir ajuste."
    )

    # Complementar quase sempre sai do escritório; a fase guarda quem assina.
    fornecedor = models.ForeignKey(
        "fornecedores.Fornecedor",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="fases",
        verbose_name="projetista responsável",
    )

    class Meta:
        ordering = ["ordem", "id"]
        verbose_name = "fase"
        verbose_name_plural = "fases"
        constraints = [
            # O complementar aberto fica de fora: um projeto pode ter vários
            # (acústico E automação), e cada um é uma fase própria.
            models.UniqueConstraint(
                fields=["projeto", "chave"],
                condition=~models.Q(chave=catalogo.CHAVE_LIVRE),
                name="fase_unica_por_projeto",
            )
        ]

    def __str__(self):
        return f"{self.projeto.nome} — {self.nome}"

    # ---- Leitura do catálogo -------------------------------------------
    @property
    def passo(self):
        return catalogo.passo(self.chave)

    @property
    def nome(self):
        if self.titulo_livre:
            return self.titulo_livre
        p = self.passo
        return p.nome if p else self.chave

    @property
    def resumo(self):
        p = self.passo
        return p.resumo if p else ""

    @property
    def entrega(self):
        p = self.passo
        return p.entrega if p else ()

    @property
    def consome(self):
        p = self.passo
        return p.consome if p else ""

    @property
    def complementar(self):
        p = self.passo
        return bool(p and p.grupo == "complementar")

    @property
    def exige_aprovacao(self):
        p = self.passo
        return bool(p and p.aprovacao_do_cliente)

    # ---- Estado ---------------------------------------------------------
    @property
    def concluida(self):
        return self.status == self.APROVADA

    @property
    def em_andamento(self):
        return self.status in self.ABERTAS

    @property
    def fase_anterior(self):
        chave = catalogo.anterior_de(self.chave)
        if chave is None:
            return None
        return self.projeto.fases.filter(chave=chave).first()

    @property
    def liberada(self):
        """Pode começar? Só depois que a anterior ter sido aprovada.

        A trava é real, e não conselho. Desenhar em cima de decisão não
        confirmada é o retrabalho mais caro do escritório, e a única forma de
        o sistema impedir isso é não deixar a fase abrir — o "eu adianto e
        depois arrumo" é justamente o hábito que ele existe para cortar.
        """
        anterior = self.fase_anterior
        return anterior is None or anterior.status == self.APROVADA

    @property
    def impedimento(self):
        if self.liberada:
            return ""
        return f"Depende de “{self.fase_anterior.nome}”, que ainda não foi aprovada."

    @property
    def atrasada(self):
        return bool(
            self.prazo and self.status != self.APROVADA and self.prazo < timezone.localdate()
        )

    # ---- Transições -----------------------------------------------------
    def abrir(self, usuario=None):
        """Deixa a fase ativa. Chamado pelo sistema, não pela pessoa.

        Clicar em "Começar" não decidia nada: a fase abre porque a anterior foi
        aprovada, e não porque alguém confirmou que sim, quer trabalhar. Um
        botão que só tem uma resposta possível é um clique cobrado à toa.
        """
        if self.status != self.NAO_INICIADA or not self.liberada:
            return False
        self.status = self.EM_ELABORACAO
        self.iniciada_em = timezone.now()
        self.save(update_fields=["status", "iniciada_em"])
        return True

    @property
    def bloqueada(self):
        return self.status == self.NAO_INICIADA and not self.liberada

    def _abrir_seguintes(self, usuario=None):
        """Aprovar uma fase acende a próxima — e os complementares, quando é o
        anteprojeto que fecha."""
        for outra in self.projeto.fases.filter(status=self.NAO_INICIADA):
            outra.abrir(usuario)

    def enviar_ao_cliente(self, usuario=None):
        if self.status not in (self.EM_ELABORACAO, self.AJUSTES):
            return False
        self.status = self.AGUARDANDO
        self.enviada_em = timezone.now()
        self.save(update_fields=["status", "enviada_em"])
        return True

    def registrar_resposta(self, aprovada, parecer="", usuario=None):
        if self.status != self.AGUARDANDO:
            return False
        self.status = self.APROVADA if aprovada else self.AJUSTES
        self.respondida_em = timezone.now()
        self.parecer = parecer
        self.save(update_fields=["status", "respondida_em", "parecer"])
        if aprovada:
            self._abrir_seguintes(usuario)
        self.projeto.tocar()
        return True

    def concluir_sem_aprovacao(self, usuario=None):
        """Para o briefing, que não vai ao cliente para aprovação formal."""
        if self.exige_aprovacao or self.status == self.APROVADA:
            return False
        self.status = self.APROVADA
        self.respondida_em = timezone.now()
        self.save(update_fields=["status", "respondida_em"])
        self._abrir_seguintes(usuario)
        self.projeto.tocar()
        return True

    def registrar(self, texto, usuario=None):
        """Anotação da fase escrita à mão. Registro automático não passa por
        aqui: o que o sistema fez mora no histórico de avisos."""
        return Lembrete.objects.create(
            empresa=self.empresa, projeto=self.projeto, fase=self,
            texto=texto, autor=usuario,
        )


class Lembrete(EmpresaModel):
    """O combinado, a conversa e o rastro — do projeto ou de uma fase dele.

    Nasceu preso à fase, mas o projeto também tem recado que não é de fase
    nenhuma ("cliente viaja em janeiro"). Em vez de um segundo modelo quase
    igual, `fase` virou opcional: sem fase, o lembrete é do projeto todo.

    Só o que a pessoa escreve. Registro automático saiu da tabela: sem tela
    que o mostrasse, era dado invisível — e o que o sistema fez já vive no
    histórico de avisos, com hora, autor e link.
    """

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="lembretes")
    fase = models.ForeignKey(
        Fase, on_delete=models.CASCADE, related_name="registros", null=True, blank=True,
        help_text="Vazio quando o lembrete é do projeto inteiro.",
    )
    texto = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-id"]
        verbose_name = "lembrete"
        verbose_name_plural = "lembretes"

    def __str__(self):
        return self.texto[:60]


def montar_fases(projeto, complementares=()):
    """Cria as fases principais do projeto e, opcionalmente, complementares.

    Idempotente: chamar de novo não duplica nada, só acrescenta o que falta.
    """
    existentes = set(projeto.fases.values_list("chave", flat=True))
    novas = []
    for ordem, p in enumerate(catalogo.TODAS):
        if p.chave in existentes:
            continue
        if p.opcional and p.chave not in complementares:
            continue
        novas.append(
            Fase(empresa=projeto.empresa, projeto=projeto, chave=p.chave, ordem=ordem)
        )
    Fase.objects.bulk_create(novas)
    # A primeira fase de um projeto novo já nasce ativa: não há nada antes dela
    # para aprovar, e deixar tudo "não iniciada" faz o projeto parecer travado.
    primeira = projeto.fases.order_by("ordem").first()
    if primeira is not None:
        primeira.abrir()
    return novas


def criar_complementares_avulsos(projeto, texto):
    """Cria uma fase para cada complementar escrito à mão, separado por vírgula.

    Nome vazio ou repetido é descartado em silêncio: o campo é de texto livre e
    quem digita "elétrico, elétrico" quis dizer um.
    """
    nomes, vistos = [], {
        f.titulo_livre.casefold()
        for f in projeto.fases.filter(chave=catalogo.CHAVE_LIVRE)
    }
    for bruto in (texto or "").split(","):
        nome = bruto.strip()
        if not nome or nome.casefold() in vistos:
            continue
        vistos.add(nome.casefold())
        nomes.append(nome)

    ordem = len(catalogo.TODAS)
    novas = [
        Fase(
            empresa=projeto.empresa, projeto=projeto,
            chave=catalogo.CHAVE_LIVRE, titulo_livre=nome, ordem=ordem + i,
        )
        for i, nome in enumerate(nomes)
    ]
    Fase.objects.bulk_create(novas)
    return novas
