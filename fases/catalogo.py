"""As fases de um projeto de arquitetura, na ordem em que acontecem.

Este arquivo é a única fonte da verdade do fluxo. Nome, o que se produz e o que
precisa estar pronto antes ficam escritos aqui uma vez; telas, roteiro e
validações leem daqui em vez de repetir a regra cada uma do seu jeito.

A sequência não é burocracia: cada fase consome o resultado da anterior. Não se
faz estudo preliminar sem o programa de necessidades, nem executivo sobre um
anteprojeto que o cliente ainda não aprovou — desenhar em cima de decisão não
confirmada é o retrabalho mais caro do escritório.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Passo:
    chave: str
    nome: str
    resumo: str
    entrega: tuple  # o que se produz nesta fase, item a item
    consome: str  # o que da fase anterior entra aqui
    opcional: bool = False
    aprovacao_do_cliente: bool = True
    grupo: str = "projeto"


# --- O caminho principal ------------------------------------------------
# Todo projeto passa por estas cinco, na ordem.
PRINCIPAIS = (
    Passo(
        chave="briefing",
        nome="Briefing",
        resumo="A conversa com o cliente virando programa de necessidades.",
        entrega=(
            "Roteiro de perguntas respondido",
            "Programa de necessidades: ambientes, metragens e uso",
            "Referências e restrições do terreno",
        ),
        consome="Os dados do cliente e do projeto.",
        aprovacao_do_cliente=False,
    ),
    Passo(
        chave="proposta",
        nome="Proposta e contrato",
        resumo="Honorários, prazos e escopo por fase — o que será entregue e quando.",
        entrega=(
            "Proposta de honorários com datas por fase",
            "Minuta de contrato",
            "Assinatura registrada",
        ),
        consome="O programa de necessidades, que define o tamanho do trabalho.",
    ),
    Passo(
        chave="estudo_preliminar",
        nome="Estudo preliminar",
        resumo="A primeira leitura do partido: referências e o esboço da planta.",
        entrega=(
            "Apresentação de conceito e referências",
            "Esboço de planta básica",
            "Verificação do programa contra a área disponível",
        ),
        consome="Briefing, programa de necessidades e referências.",
    ),
    Passo(
        chave="anteprojeto",
        nome="Anteprojeto",
        resumo="O projeto ganha forma: planta definida, volume e materiais.",
        entrega=(
            "Plantas, cortes e fachadas em nível de anteprojeto",
            "Modelo 3D e imagens",
            "Materiais e sistemas construtivos",
        ),
        consome="O estudo preliminar aprovado.",
    ),
    Passo(
        chave="executivo",
        nome="Projeto executivo",
        resumo="O detalhamento que vai para a obra: cotas, quantitativos e especificação.",
        entrega=(
            "Plantas, cortes e fachadas cotados",
            "Detalhamentos e quantitativos",
            "Memorial descritivo e especificações",
        ),
        consome="O anteprojeto aprovado.",
    ),
)

# --- Os complementares --------------------------------------------------
# Opcionais e sob demanda: nem todo trabalho tem algum, quase nenhum tem todos.
# Começam a partir do anteprojeto, porque é aí que existe planta para calcular.
COMPLEMENTARES = (
    Passo(
        chave="comp_estrutural",
        nome="Projeto estrutural",
        resumo="Cálculo e detalhamento da estrutura.",
        entrega=("Lançamento estrutural", "Dimensionamento", "Detalhamento e ferragem"),
        consome="O anteprojeto aprovado.",
        opcional=True,
        grupo="complementar",
    ),
    Passo(
        chave="comp_eletrica",
        nome="Projeto elétrico",
        resumo="Pontos, circuitos, quadros e luminotécnico.",
        entrega=("Pontos e circuitos", "Quadro de cargas", "Luminotécnico"),
        consome="O anteprojeto aprovado.",
        opcional=True,
        grupo="complementar",
    ),
    Passo(
        chave="comp_hidraulica",
        nome="Projeto hidrossanitário",
        resumo="Água fria e quente, esgoto e pluvial.",
        entrega=("Água fria e quente", "Esgoto e pluvial", "Reservação e detalhes"),
        consome="O anteprojeto aprovado.",
        opcional=True,
        grupo="complementar",
    ),
    # O escritório encontra complementar que não cabe em lista fechada:
    # acústico, luminotécnico, automação, impermeabilização. Em vez de crescer
    # a lista para sempre, existe um tipo aberto que carrega o próprio nome.
    Passo(
        chave="comp_outro",
        nome="Complementar",
        resumo="Um complementar específico deste projeto.",
        entrega=("Projeto e detalhamento", "Compatibilização com o arquitetônico"),
        consome="O anteprojeto aprovado.",
        opcional=True,
        grupo="complementar",
    ),
    Passo(
        chave="comp_paisagismo",
        nome="Paisagismo",
        resumo="Massas vegetais, espécies e irrigação.",
        entrega=("Planta de paisagismo", "Lista de espécies", "Irrigação e drenagem"),
        consome="O anteprojeto aprovado.",
        opcional=True,
        grupo="complementar",
    ),
)

CHAVE_LIVRE = "comp_outro"
# A oferta em caixas mostra só os complementares nomeados; o aberto tem campo
# de texto e não faz sentido como caixa de marcar.
COMPLEMENTARES_NOMEADOS = tuple(p for p in COMPLEMENTARES if p.chave != CHAVE_LIVRE)

TODAS = PRINCIPAIS + COMPLEMENTARES
POR_CHAVE = {p.chave: p for p in TODAS}
CHOICES = [(p.chave, p.nome) for p in TODAS]

# A fase que precisa estar aprovada para cada complementar começar.
PRE_REQUISITO_COMPLEMENTAR = "anteprojeto"


def passo(chave):
    return POR_CHAVE.get(chave)


def anterior_de(chave):
    """A fase principal imediatamente anterior, ou None se for a primeira.

    Complementar não tem anterior na fila principal: todos dependem do mesmo
    anteprojeto e correm em paralelo entre si.
    """
    p = POR_CHAVE.get(chave)
    if p is None:
        return None
    if p.grupo == "complementar":
        return PRE_REQUISITO_COMPLEMENTAR
    chaves = [x.chave for x in PRINCIPAIS]
    i = chaves.index(chave)
    return chaves[i - 1] if i > 0 else None
