"""Questionário público de maturidade em gestão (stateless, sem persistência).
5 perguntas × 4 dimensões, 0–2 pontos por resposta, máximo 10 pontos."""

PERGUNTAS = [
    {
        "id": "projetos",
        "dimensao": "Controle de projetos",
        "texto": "Como você acompanha o andamento dos seus projetos?",
        "opcoes": [
            ("De cabeça ou por conversas soltas.", 0),
            ("Em uma planilha ou anotações separadas.", 1),
            ("Em um painel único com etapa e pendências de cada projeto.", 2),
        ],
    },
    {
        "id": "prazos",
        "dimensao": "Prazos",
        "texto": "Você sabe, agora, quais projetos estão parados ou atrasados?",
        "opcoes": [
            ("Só percebo quando o cliente cobra.", 0),
            ("Descubro se eu for procurar.", 1),
            ("Recebo alerta automático de projeto parado e prazo.", 2),
        ],
    },
    {
        "id": "precificacao",
        "dimensao": "Precificação",
        "texto": "Como você define o valor da hora técnica e das propostas?",
        "opcoes": [
            ("Por comparação com o mercado ou 'no feeling'.", 0),
            ("Tenho uma conta aproximada, feita uma vez.", 1),
            ("Calculo pela minha estrutura de custos e ajusto por projeto.", 2),
        ],
    },
    {
        "id": "financeiro",
        "dimensao": "Financeiro",
        "texto": "Você sabe a margem real de cada projeto entregue?",
        "opcoes": [
            ("Não separo o financeiro por projeto.", 0),
            ("Tenho uma noção geral do caixa.", 1),
            ("Vejo receita, custo de horas e margem por projeto.", 2),
        ],
    },
    {
        "id": "tarefas",
        "dimensao": "Tarefas e equipe",
        "texto": "Como as tarefas são distribuídas e cobradas?",
        "opcoes": [
            ("Verbalmente, sem registro.", 0),
            ("Em uma lista, mas sem dono ou prazo claros.", 1),
            ("Com responsável, prazo e critério de pronto.", 2),
        ],
    },
]

FAIXAS = [
    (0, 3, "Inicial", "A gestão ainda depende de memória e improviso. Pequenas estruturas já destravam muito: um painel de projetos e uma hora técnica calculada."),
    (4, 7, "Intermediário", "Você já tem controle parcial. O ganho agora está em unificar projetos, financeiro e prazos num lugar só, com alertas."),
    (8, 10, "Avançado", "Sua operação é madura. O sistema serve para escalar sem perder a visão de margem e de conformidade."),
]

PONTOS_MAXIMO = len(PERGUNTAS) * 2


def avaliar(respostas):
    """respostas: dict {pergunta_id: indice_opcao}. Retorna (pontos, faixa, descricao)."""
    pontos = 0
    for pergunta in PERGUNTAS:
        try:
            indice = int(respostas.get(pergunta["id"]))
            if indice < 0:
                continue
            pontos += pergunta["opcoes"][indice][1]
        except (ValueError, IndexError, TypeError):
            continue
    for minimo, maximo, faixa, descricao in FAIXAS:
        if minimo <= pontos <= maximo:
            return pontos, faixa, descricao
    return pontos, "Inicial", FAIXAS[0][3]
