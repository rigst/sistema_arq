"""Roteiros de briefing que já vêm prontos.

O escritório pode editar, duplicar ou apagar. A ideia é que ninguém precise
começar de uma folha em branco: as opções cobrem as respostas que aparecem em
90% das reuniões, e o campo de complemento guarda o resto.
"""

RESIDENCIAL = {
    "nome": "Residencial — interiores",
    "tipo_projeto": "residencial",
    "descricao": "Roteiro para reforma ou interiores de residência, do perfil do morador ao estilo.",
    "perguntas": [
        {
            "bloco": "Quem mora",
            "texto": "Quem vai usar o espaço no dia a dia?",
            "tipo": "multipla",
            "opcoes": [
                "Casal sem filhos",
                "Casal com filhos pequenos",
                "Casal com filhos adolescentes",
                "Mora sozinho(a)",
                "Casa multigeracional (pais ou sogros)",
                "Recebe visita com frequência",
                "Tem animal de estimação",
            ],
        },
        {
            "bloco": "Quem mora",
            "texto": "Alguém trabalha em casa?",
            "tipo": "opcao",
            "opcoes": [
                "Não",
                "Sim, ocasionalmente",
                "Sim, em tempo integral",
                "Sim, e recebe clientes em casa",
            ],
        },
        {
            "bloco": "Rotina",
            "texto": "Onde a família passa mais tempo junta?",
            "tipo": "multipla",
            "opcoes": ["Sala de estar", "Cozinha", "Varanda ou área externa", "Sala de jantar", "Home theater"],
        },
        {
            "bloco": "Rotina",
            "texto": "Como é a rotina de cozinhar?",
            "tipo": "opcao",
            "opcoes": [
                "Cozinha todo dia, precisa de bancada e armazenamento",
                "Cozinha no fim de semana",
                "Quase não cozinha",
                "Tem quem cozinhe para a família",
            ],
        },
        {
            "bloco": "Escopo",
            "texto": "O que entra na reforma?",
            "tipo": "multipla",
            "opcoes": [
                "Layout e alvenaria",
                "Marcenaria sob medida",
                "Elétrica e iluminação",
                "Hidráulica",
                "Revestimentos e pisos",
                "Mobiliário solto e decoração",
                "Só consultoria e projeto",
            ],
        },
        {
            "bloco": "Escopo",
            "texto": "O imóvel está ocupado durante a obra?",
            "tipo": "opcao",
            "opcoes": [
                "Vazio, obra livre",
                "Ocupado, obra por etapas",
                "Ocupado, família sai durante a obra",
            ],
        },
        {
            "bloco": "Orçamento e prazo",
            "texto": "Como está definido o orçamento de execução?",
            "tipo": "opcao",
            "opcoes": [
                "Valor fechado e inegociável",
                "Valor de referência, com folga",
                "Ainda não definido — quer estimativa do escritório",
                "Vai executar por etapas conforme o caixa",
            ],
        },
        {
            "bloco": "Orçamento e prazo",
            "texto": "Existe uma data que não pode passar?",
            "tipo": "opcao",
            "opcoes": [
                "Não, o prazo é flexível",
                "Sim, mudança marcada",
                "Sim, evento de família",
                "Sim, fim de contrato de aluguel",
            ],
        },
        {
            "bloco": "Estilo",
            "texto": "Que atmosfera o cliente busca?",
            "tipo": "multipla",
            "opcoes": [
                "Aconchegante e informal",
                "Clean e minimalista",
                "Contemporâneo com cor",
                "Clássico e atemporal",
                "Industrial",
                "Natural, madeira e verde",
            ],
        },
        {
            "bloco": "Estilo",
            "texto": "Tem algo que o cliente já disse que não quer?",
            "tipo": "texto",
            "ajuda": "Cores, materiais, soluções vetadas — anote nas palavras dele.",
        },
        {
            "bloco": "Restrições",
            "texto": "Restrições do imóvel ou do condomínio",
            "tipo": "multipla",
            "opcoes": [
                "Condomínio com regras de horário",
                "Não pode mexer em estrutura",
                "Prédio tombado ou em área de preservação",
                "Necessita aprovação em prefeitura",
                "Sem restrições conhecidas",
            ],
        },
        {
            "bloco": "Restrições",
            "texto": "O que mais precisa ficar registrado?",
            "tipo": "texto",
            "ajuda": "Qualquer coisa dita na reunião que não coube nas perguntas acima.",
        },
    ],
}

COMERCIAL = {
    "nome": "Comercial — loja e escritório",
    "tipo_projeto": "comercial",
    "descricao": "Roteiro para ponto comercial, com operação, público e identidade.",
    "perguntas": [
        {
            "bloco": "Operação",
            "texto": "Qual é a operação do espaço?",
            "tipo": "opcao",
            "opcoes": [
                "Loja de varejo",
                "Escritório administrativo",
                "Consultório ou clínica",
                "Restaurante ou café",
                "Espaço de serviços (salão, estúdio)",
            ],
        },
        {
            "bloco": "Operação",
            "texto": "Quantas pessoas ocupam o espaço ao mesmo tempo?",
            "tipo": "opcao",
            "opcoes": ["Até 5", "De 6 a 15", "De 16 a 40", "Mais de 40"],
        },
        {
            "bloco": "Operação",
            "texto": "Qual é o horário de funcionamento?",
            "tipo": "opcao",
            "opcoes": ["Comercial", "Estendido, inclui noite", "Fim de semana também", "24 horas"],
        },
        {
            "bloco": "Público",
            "texto": "Quem é o público que entra ali?",
            "tipo": "texto",
            "ajuda": "Perfil, faixa etária, o que a pessoa espera sentir ao entrar.",
        },
        {
            "bloco": "Escopo",
            "texto": "O que entra no projeto?",
            "tipo": "multipla",
            "opcoes": [
                "Layout e circulação",
                "Identidade visual aplicada ao espaço",
                "Marcenaria e expositores",
                "Iluminação técnica",
                "Climatização",
                "Acessibilidade (NBR 9050)",
                "Prevenção de incêndio",
            ],
        },
        {
            "bloco": "Restrições",
            "texto": "Que aprovações o ponto exige?",
            "tipo": "multipla",
            "opcoes": [
                "Vigilância sanitária",
                "Corpo de bombeiros",
                "Prefeitura / alvará",
                "Regras do shopping ou do condomínio",
                "Nenhuma conhecida",
            ],
        },
        {
            "bloco": "Orçamento e prazo",
            "texto": "Existe data de inauguração?",
            "tipo": "opcao",
            "opcoes": ["Não", "Sim, data firme", "Sim, mas negociável"],
        },
        {
            "bloco": "Orçamento e prazo",
            "texto": "O que mais precisa ficar registrado?",
            "tipo": "texto",
        },
    ],
}

ARQUITETURA_RESIDENCIAL = {
    "nome": "Residencial — arquitetura e reforma",
    "tipo_projeto": "residencial",
    "descricao": "Programa, terreno, restrições, orçamento e critérios de desempenho para casas e reformas.",
    "perguntas": [
        {
            "bloco": "Pessoas e rotina",
            "texto": "Quem usará a edificação agora e nos próximos anos?",
            "tipo": "multipla",
            "opcoes": [
                "Adultos",
                "Crianças",
                "Idosos",
                "Pessoa com mobilidade reduzida",
                "Animais de estimação",
                "Funcionários ou prestadores recorrentes",
            ],
        },
        {
            "bloco": "Programa",
            "texto": "Quais usos precisam ter prioridade no programa?",
            "tipo": "multipla",
            "opcoes": [
                "Convívio e receber",
                "Trabalho em casa",
                "Cozinhar",
                "Descanso e privacidade",
                "Lazer externo",
                "Acessibilidade e permanência no imóvel",
            ],
        },
        {
            "bloco": "Programa",
            "texto": "Há ambientes, equipamentos ou mobiliário que precisam ser preservados?",
            "tipo": "texto",
            "ajuda": "Registre dimensões, peças afetivas e equipamentos com requisitos específicos.",
        },
        {
            "bloco": "Terreno e imóvel",
            "texto": "Quais levantamentos e documentos já estão disponíveis?",
            "tipo": "multipla",
            "opcoes": [
                "Matrícula atualizada",
                "Levantamento topográfico",
                "Sondagem",
                "Plantas existentes",
                "Regras de condomínio",
                "Consulta de zoneamento",
                "Nenhum ainda",
            ],
        },
        {
            "bloco": "Desempenho",
            "texto": "Quais critérios de conforto são mais importantes?",
            "tipo": "multipla",
            "opcoes": [
                "Iluminação natural",
                "Ventilação natural",
                "Conforto térmico",
                "Conforto acústico",
                "Baixa manutenção",
                "Eficiência energética e hídrica",
            ],
        },
        {
            "bloco": "Escopo",
            "texto": "Quais serviços o cliente espera contratar?",
            "tipo": "multipla",
            "opcoes": [
                "Estudo preliminar",
                "Anteprojeto",
                "Projeto legal",
                "Projeto executivo",
                "Compatibilização de complementares",
                "Orçamento",
                "Acompanhamento da execução",
            ],
        },
        {
            "bloco": "Orçamento e prazo",
            "texto": "Qual é a faixa de investimento disponível para a execução?",
            "tipo": "texto",
            "ajuda": "Diferencie orçamento da obra, honorários e itens adquiridos diretamente.",
        },
        {
            "bloco": "Orçamento e prazo",
            "texto": "Existe uma data externa que condiciona o cronograma?",
            "tipo": "multipla",
            "opcoes": [
                "Mudança",
                "Fim de locação",
                "Financiamento",
                "Aprovação pública",
                "Evento",
                "Não há data rígida",
            ],
        },
        {
            "bloco": "Decisão e comunicação",
            "texto": "Quem aprova as decisões e como os retornos serão formalizados?",
            "tipo": "texto",
            "ajuda": "Defina responsáveis, canal e prazo esperado para aprovações.",
        },
    ],
}

PADROES = [ARQUITETURA_RESIDENCIAL, RESIDENCIAL, COMERCIAL]
