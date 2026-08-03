"""Itens de proposta que todo escritório escreve de novo a cada projeto.

A proposta é o documento que o arquiteto mais adia, e a razão é sempre a mesma:
começar de uma folha em branco às dez da noite. Aqui estão as linhas que se
repetem — as fases do projeto e os serviços que costumam ser cobrados à parte —
com uma estimativa de horas para servir de ponto de partida, não de verdade.

As horas são deliberadamente redondas. Precisão falsa num padrão é pior do que
número redondo: convence a pessoa a não conferir.
"""

from fases import catalogo

# (etapa, horas sugeridas, o que inclui). A ordem é a do fluxo contratado.
FASES_DE_PROJETO = [
    ("Briefing e programa de necessidades", 8, "Reunião de briefing, roteiro respondido e consolidação dos ambientes e metragens."),
    ("Levantamento e estudo de viabilidade", 12, "Levantamento das informações disponíveis, condicionantes e análise inicial de viabilidade."),
    ("Estudo preliminar", 40, "Conceito, referências, implantação ou layout inicial e apresentação para aprovação."),
    ("Anteprojeto", 60, "Plantas, cortes, fachadas, volumetria e definição preliminar de materiais e sistemas."),
    ("Projeto legal e aprovação em prefeitura", 30, "Peças gráficas e documentação técnica para protocolo; taxas e prazos do órgão não inclusos."),
    ("Projeto executivo", 80, "Desenhos executivos cotados, detalhamentos construtivos e informações para execução."),
    ("Detalhamento de marcenaria", 40, "Vistas, cortes, dimensões, materiais e ferragens dos móveis previstos no escopo."),
    ("Memorial descritivo e especificações", 16, "Especificação de materiais, acabamentos, componentes e critérios de execução."),
]

SERVICOS_AVULSOS = [
    ("Coordenação de projetos complementares", 20, "Análise de interferências e consolidação das disciplinas contratadas à parte."),
    ("Acompanhamento de obra (por visita)", 4, "Uma visita técnica e relatório; não inclui gerenciamento da obra."),
    ("Assessoria de compras e fornecedores", 12, "Curadoria, cotações e apoio à escolha; compras e contratos são feitos pelo cliente."),
    ("Projeto luminotécnico", 24, "Conceito, distribuição de luminárias, comandos e especificação básica."),
    ("Projeto de paisagismo", 20, "Conceito, plano de massas, espécies e orientações de implantação."),
    ("Maquete eletrônica e imagens", 30, "Modelagem tridimensional e imagens das vistas definidas no escopo."),
    ("Reunião extra com o cliente", 3, "Uma reunião adicional, preparação, registro e encaminhamentos."),
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
    inclusoes = {nome: detalhe for nome, _, detalhe in FASES_DE_PROJETO}
    return [
        (p.nome, horas.get(p.chave, 20), inclusoes.get(p.nome, p.resumo))
        for p in catalogo.PRINCIPAIS
        if p.chave not in {"proposta", "contrato"}
    ]
