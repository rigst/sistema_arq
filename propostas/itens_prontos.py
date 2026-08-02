"""Itens de proposta que todo escritório escreve de novo a cada projeto.

A proposta é o documento que o arquiteto mais adia, e a razão é sempre a mesma:
começar de uma folha em branco às dez da noite. Aqui estão as linhas que se
repetem — as fases do projeto e os serviços que costumam ser cobrados à parte —
com uma estimativa de horas para servir de ponto de partida, não de verdade.

As horas são deliberadamente redondas. Precisão falsa num padrão é pior do que
número redondo: convence a pessoa a não conferir.
"""

from fases import catalogo

# (descrição, horas sugeridas). A ordem é a do fluxo.
FASES_DE_PROJETO = [
    ("Levantamento e estudo de viabilidade", 12),
    ("Briefing e programa de necessidades", 8),
    ("Estudo preliminar", 40),
    ("Anteprojeto", 60),
    ("Projeto legal e aprovação em prefeitura", 30),
    ("Projeto executivo", 80),
    ("Detalhamento de marcenaria", 40),
    ("Memorial descritivo e especificações", 16),
]

SERVICOS_AVULSOS = [
    ("Coordenação de projetos complementares", 20),
    ("Acompanhamento de obra (por visita)", 4),
    ("Assessoria de compras e fornecedores", 12),
    ("Projeto luminotécnico", 24),
    ("Projeto de paisagismo", 20),
    ("Maquete eletrônica e imagens", 30),
    ("Reunião extra com o cliente", 3),
]


def por_grupo():
    """Os prontos em dois grupos, para a tela oferecer sem virar lista longa."""
    return [
        ("Fases do projeto", FASES_DE_PROJETO),
        ("Serviços à parte", SERVICOS_AVULSOS),
    ]


def para_o_tipo(tipo_projeto):
    """Todas as fases do catálogo viram itens sugeridos.

    O catálogo de fases já é a espinha do sistema; oferecer as mesmas etapas na
    proposta mantém a promessa alinhada com o que vai ser entregue.
    """
    horas = {
        "briefing": 8,
        "proposta": 4,
        "estudo_preliminar": 40,
        "anteprojeto": 60,
        "executivo": 80,
    }
    return [(p.nome, horas.get(p.chave, 20)) for p in catalogo.PRINCIPAIS]
