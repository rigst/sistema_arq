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
        """Pode começar? Só depois que a anterior foi aprovada.

        A trava é informativa, não policial: o sistema mostra o que falta e
        deixa a decisão com o arquiteto, porque na prática se adianta trabalho
        enquanto o cliente demora para responder.
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
    def iniciar(self, usuario=None):
        if self.status != self.NAO_INICIADA:
            return False
        self.status = self.EM_ELABORACAO
        self.iniciada_em = timezone.now()
        self.save(update_fields=["status", "iniciada_em"])
        self.registrar("sistema", "Fase iniciada.", usuario)
        return True

    def enviar_ao_cliente(self, usuario=None):
        if self.status not in (self.EM_ELABORACAO, self.AJUSTES):
            return False
        self.status = self.AGUARDANDO
        self.enviada_em = timezone.now()
        self.save(update_fields=["status", "enviada_em"])
        self.registrar("sistema", "Enviada ao cliente para aprovação.", usuario)
        return True

    def registrar_resposta(self, aprovada, parecer="", usuario=None):
        if self.status != self.AGUARDANDO:
            return False
        self.status = self.APROVADA if aprovada else self.AJUSTES
        self.respondida_em = timezone.now()
        self.parecer = parecer
        self.save(update_fields=["status", "respondida_em", "parecer"])
        verbo = "aprovou" if aprovada else "pediu ajustes"
        self.registrar("cliente", f"Cliente {verbo}. {parecer}".strip(), usuario)
        self.projeto.tocar()
        return True

    def concluir_sem_aprovacao(self, usuario=None):
        """Para o briefing, que não vai ao cliente para aprovação formal."""
        if self.exige_aprovacao or self.status == self.APROVADA:
            return False
        self.status = self.APROVADA
        self.respondida_em = timezone.now()
        self.save(update_fields=["status", "respondida_em"])
        self.registrar("sistema", "Fase concluída.", usuario)
        self.projeto.tocar()
        return True

    def registrar(self, tipo, texto, usuario=None, fixado=False):
        return Lembrete.objects.create(
            empresa=self.empresa, projeto=self.projeto, fase=self, tipo=tipo,
            texto=texto, autor=usuario, fixado=fixado,
        )


class Lembrete(EmpresaModel):
    """O combinado, a conversa e o rastro — do projeto ou de uma fase dele.

    Nasceu preso à fase, mas o projeto também tem recado que não é de fase
    nenhuma ("cliente viaja em janeiro"). Em vez de um segundo modelo quase
    igual, `fase` virou opcional: sem fase, o lembrete é do projeto todo.

    Comentário e registro automático moram na mesma tabela de propósito.
    Separar em duas obriga a cruzar horários na cabeça para entender por que
    uma versão mudou; o que separa os dois é o campo `fixado`.
    """

    TIPO_CHOICES = [
        ("comentario", "Comentário interno"),
        ("cliente", "Conversa com o cliente"),
        ("sistema", "Registro do sistema"),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="lembretes")
    fase = models.ForeignKey(
        Fase, on_delete=models.CASCADE, related_name="registros", null=True, blank=True,
        help_text="Vazio quando o lembrete é do projeto inteiro.",
    )
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, default="comentario")
    texto = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Fixado = post-it no topo da fase. O que a pessoa escreve à mão nasce
    # fixado, porque foi escrito para ser lembrado; o que o sistema registra
    # nasce arquivado, porque é rastro e não recado.
    fixado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-id"]
        verbose_name = "lembrete"
        verbose_name_plural = "lembretes"

    def __str__(self):
        return f"{self.fase or self.projeto} — {self.get_tipo_display()}"

    @property
    def do_sistema(self):
        return self.tipo == "sistema"


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
