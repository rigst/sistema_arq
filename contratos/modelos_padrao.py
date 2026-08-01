"""Minutas que já vêm prontas, para o escritório partir de algo em vez do zero.

São rascunhos de trabalho, não peça jurídica pronta: mande revisar por um
advogado antes de usar com cliente real. Os campos entre chaves duplas são
trocados pelos dados do projeto na hora de gerar.
"""

PROJETO_ARQUITETONICO = {
    "nome": "Projeto arquitetônico — pessoa física",
    "descricao": "Prestação de serviços de projeto para cliente pessoa física.",
    "padrao": True,
    "corpo": """CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE ARQUITETURA

CONTRATANTE: {{cliente}}, inscrito(a) no CPF/CNPJ sob o nº {{cliente_documento}}.
CONTRATADA: {{escritorio}}.

CLÁUSULA 1 — DO OBJETO
A CONTRATADA prestará serviços de arquitetura para o projeto "{{projeto}}", da \
categoria {{tipo_projeto}}, a ser executado no imóvel situado em {{endereco}}.

CLÁUSULA 2 — DAS ETAPAS E ENTREGÁVEIS
Os serviços compreendem levantamento, estudo preliminar, anteprojeto, projeto \
legal e projeto executivo, com os entregáveis descritos na proposta que integra \
este contrato. Cada etapa depende da aprovação formal da anterior.

CLÁUSULA 3 — DO PRAZO
O prazo de entrega é {{prazo}}, contado do aceite deste contrato e do pagamento \
da primeira parcela. Prazos de aprovação em órgãos públicos e o tempo de resposta \
do CONTRATANTE não integram esta contagem.

CLÁUSULA 4 — DOS HONORÁRIOS
Os honorários são de {{valor}}, pagos conforme o cronograma financeiro anexo. \
O atraso superior a 15 dias suspende os serviços até a regularização.

CLÁUSULA 5 — DO REAJUSTE
Contratos com execução superior a 12 meses têm os valores remanescentes \
reajustados pelo [ÍNDICE DE REAJUSTE].

CLÁUSULA 6 — DAS OBRIGAÇÕES DO CONTRATANTE
Fornecer documentação do imóvel, matrícula, levantamento topográfico quando \
necessário, e responder às consultas da CONTRATADA em até [PRAZO DE RESPOSTA] \
dias úteis.

CLÁUSULA 7 — DAS ALTERAÇÕES DE ESCOPO
Alterações solicitadas após a aprovação de uma etapa serão orçadas à parte e \
formalizadas por aditivo, com impacto em prazo e valor.

CLÁUSULA 8 — DA PROPRIEDADE INTELECTUAL
O projeto é protegido pela Lei 9.610/98 e pela Lei 12.378/2010. A CONTRATADA \
cede ao CONTRATANTE o direito de uso para a obra objeto deste contrato, vedadas \
reprodução em outro terreno, revenda ou alteração sem anuência do autor.

CLÁUSULA 9 — DA RESPONSABILIDADE TÉCNICA
A CONTRATADA emitirá RRT junto ao CAU para os serviços contratados. A execução \
da obra e a responsabilidade por ela são de terceiro contratado pelo CONTRATANTE, \
salvo contratação específica de acompanhamento.

CLÁUSULA 10 — DA RESCISÃO
Qualquer parte pode rescindir mediante aviso de 30 dias. São devidos os \
honorários das etapas concluídas e o proporcional da etapa em andamento.

CLÁUSULA 11 — DO FORO
Fica eleito o foro da comarca de [COMARCA] para dirimir controvérsias.

{{data}}

_______________________________        _______________________________
{{cliente}}                             {{escritorio}}
""",
}

INTERIORES = {
    "nome": "Interiores com acompanhamento de obra",
    "descricao": "Projeto de interiores incluindo visitas e gestão de fornecedores.",
    "padrao": False,
    "corpo": """CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE DESIGN DE INTERIORES

CONTRATANTE: {{cliente}}, CPF/CNPJ nº {{cliente_documento}}.
CONTRATADA: {{escritorio}}.

CLÁUSULA 1 — DO OBJETO
Projeto de interiores para "{{projeto}}", no imóvel situado em {{endereco}}, \
incluindo layout, detalhamento de marcenaria, especificação de acabamentos, \
iluminação e mobiliário.

CLÁUSULA 2 — DO ACOMPANHAMENTO DE OBRA
Estão incluídas [NÚMERO] visitas técnicas ao longo da execução, com relatório \
de cada visita. Visitas adicionais são cobradas a [VALOR DA VISITA] cada.

CLÁUSULA 3 — DOS FORNECEDORES
A CONTRATADA indica fornecedores e acompanha a execução, mas a contratação é \
feita diretamente pelo CONTRATANTE. A CONTRATADA não responde por prazo, preço \
ou qualidade de terceiros contratados pelo CONTRATANTE.

CLÁUSULA 4 — DO PRAZO
Entrega do projeto em {{prazo}}. O acompanhamento se encerra em [PRAZO DE OBRA] \
ou na conclusão da obra, o que ocorrer primeiro.

CLÁUSULA 5 — DOS HONORÁRIOS
{{valor}}, pagos conforme cronograma anexo.

CLÁUSULA 6 — DAS ALTERAÇÕES
Alterações após a aprovação do projeto executivo serão orçadas à parte e \
formalizadas por aditivo.

CLÁUSULA 7 — DA PROPRIEDADE INTELECTUAL
Aplicam-se a Lei 9.610/98 e a Lei 12.378/2010. O uso do projeto é restrito ao \
imóvel objeto deste contrato.

CLÁUSULA 8 — DA RESCISÃO
Aviso prévio de 30 dias, com pagamento das etapas concluídas e do proporcional \
da etapa em curso.

CLÁUSULA 9 — DO FORO
Foro da comarca de [COMARCA].

{{data}}

_______________________________        _______________________________
{{cliente}}                             {{escritorio}}
""",
}

MODELOS_PADRAO = [PROJETO_ARQUITETONICO, INTERIORES]
