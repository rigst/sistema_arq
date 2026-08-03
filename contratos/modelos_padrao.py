"""Minutas que já vêm prontas, para o escritório partir de algo em vez do zero.

São rascunhos de trabalho, não peça jurídica pronta: mande revisar por um
advogado antes de usar com cliente real. Os campos entre chaves duplas são
trocados pelos dados do projeto na hora de gerar.
"""

PROJETO_ARQUITETONICO = {
    "nome": "Projeto arquitetônico — pessoa física",
    "descricao": "Prestação de serviços de projeto para cliente pessoa física.",
    "padrao": True,
    "tipo_projeto": "residencial",
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

ESCOPO E HONORÁRIOS DA PROPOSTA
{{escopo}}

CLÁUSULA 3 — DO PRAZO
O prazo de entrega é {{prazo}}, contado do aceite deste contrato e do pagamento \
da primeira parcela. Prazos de aprovação em órgãos públicos e o tempo de resposta \
do CONTRATANTE não integram esta contagem.

CRONOGRAMA PREVISTO
{{cronograma}}

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

CRONOGRAMA PREVISTO
{{cronograma}}

CLÁUSULA 5 — DOS HONORÁRIOS
{{valor}}, pagos conforme cronograma anexo.

ESCOPO E HONORÁRIOS DA PROPOSTA
{{escopo}}

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

COMERCIAL = {
    "nome": "Projeto comercial — pessoa jurídica",
    "descricao": "Projeto para loja, escritório ou serviço, com aprovações, sigilo e responsabilidades definidos.",
    "padrao": False,
    "tipo_projeto": "comercial",
    "corpo": """CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE ARQUITETURA

CONTRATANTE: {{cliente}}, inscrito(a) no CPF/CNPJ sob o nº {{cliente_documento}}.
CONTRATADA: {{escritorio}}.

CLÁUSULA 1 — DO OBJETO E DO ESCOPO
A CONTRATADA desenvolverá o projeto "{{projeto}}", no endereço {{endereco}}, conforme etapas, limites e entregáveis aprovados na proposta comercial.

ESCOPO E HONORÁRIOS DA PROPOSTA
{{escopo}}

CLÁUSULA 2 — DOS ENTREGÁVEIS E DAS APROVAÇÕES
Cada etapa será entregue para análise do CONTRATANTE. A etapa seguinte começa após aprovação formal da anterior. Arquivos editáveis, imagens adicionais e serviços não descritos na proposta não integram o escopo.

CLÁUSULA 3 — DO CRONOGRAMA
O início previsto é {{data_inicio}} e a conclusão prevista é {{prazo}}, condicionados ao recebimento de documentos, aprovações e pagamentos nas datas acordadas.

CRONOGRAMA PREVISTO
{{cronograma}}

CLÁUSULA 4 — DOS HONORÁRIOS E PAGAMENTOS
Os honorários totalizam {{valor}} e serão pagos conforme o parcelamento acordado. O atraso autoriza a suspensão dos serviços e a reprogramação das datas de entrega.

CLÁUSULA 5 — DAS RESPONSABILIDADES DO CONTRATANTE
O CONTRATANTE fornecerá documentos, levantamentos, regras do imóvel e informações operacionais corretas, indicará um responsável pelas decisões e responderá às solicitações em até [PRAZO] dias úteis.

CLÁUSULA 6 — DAS APROVAÇÕES E LICENÇAS
Taxas, emolumentos e prazos de órgãos públicos, condomínio, Corpo de Bombeiros, Vigilância Sanitária e concessionárias não estão incluídos, salvo indicação expressa na proposta.

CLÁUSULA 7 — DAS ALTERAÇÕES CONTRATUAIS
Mudanças de programa, área, operação ou decisões já aprovadas serão registradas como alteração de escopo ou aditivo, com eventual revisão de valor e prazo.

CLÁUSULA 8 — DA RESPONSABILIDADE TÉCNICA
A CONTRATADA emitirá o RRT correspondente aos serviços sob sua responsabilidade. Projetos complementares e execução terão responsáveis técnicos próprios quando não integrarem o escopo contratado.

CLÁUSULA 9 — DOS DIREITOS AUTORAIS E DO USO
O projeto destina-se exclusivamente ao imóvel deste contrato. Reprodução, alteração ou implantação em outro local depende de autorização escrita do autor, observadas as Leis 9.610/1998 e 12.378/2010.

CLÁUSULA 10 — DO SIGILO E DA COMUNICAÇÃO
As partes preservarão informações comerciais e operacionais confidenciais. Decisões, aprovações e solicitações relevantes serão formalizadas por escrito no canal acordado.

CLÁUSULA 11 — DA RESCISÃO E DO ENCERRAMENTO
A rescisão exige comunicação escrita com antecedência de [PRAZO]. Permanecem devidos os serviços concluídos e o proporcional da etapa em andamento, com entrega formal dos produtos já pagos.

CLÁUSULA 12 — DO FORO
Fica eleito o foro da comarca de [COMARCA], sem prejuízo de tentativa prévia de composição entre as partes.

{{data}}

_______________________________        _______________________________
{{cliente}}                             {{escritorio}}
""",
}

def _modelo_por_tipo(tipo, rotulo, objeto, requisitos):
    return {
        "nome": f"{rotulo} — prestação de serviços",
        "tipo_projeto": tipo,
        "descricao": f"Minuta-base para projeto {rotulo.lower()}, editável antes do envio.",
        "padrao": False,
        "corpo": f"""CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE ARQUITETURA E URBANISMO

CONTRATANTE: {{{{cliente}}}}, CPF/CNPJ nº {{{{cliente_documento}}}}.
CONTRATADA: {{{{escritorio}}}}.

CLÁUSULA 1 — OBJETO
Desenvolvimento de {objeto} para “{{{{projeto}}}}”, em {{{{endereco}}}}, conforme a proposta aprovada.

CLÁUSULA 2 — ESCOPO E ENTREGÁVEIS
{{{{escopo}}}}
O trabalho observará especialmente: {requisitos}. Serviços não descritos serão objeto de proposta adicional.

CLÁUSULA 3 — ETAPAS E PRAZOS
As etapas seguem a ordem abaixo. Os prazos são contados em dias úteis a partir da assinatura e cada etapa depende da aprovação da anterior.
{{{{cronograma}}}}
O tempo de análise do CONTRATANTE, de órgãos públicos e de terceiros suspende a contagem.

CLÁUSULA 4 — HONORÁRIOS
Os honorários totalizam {{{{valor}}}}, pagos conforme o cronograma financeiro acordado.

CLÁUSULA 5 — OBRIGAÇÕES E APROVAÇÕES
O CONTRATANTE fornecerá documentos e decisões no prazo acordado. Aprovações de etapa serão formalizadas por escrito.

CLÁUSULA 6 — ALTERAÇÕES
Mudanças após aprovação de etapa serão avaliadas quanto a prazo e valor e formalizadas por aditivo.

CLÁUSULA 7 — RESPONSABILIDADE TÉCNICA E DIREITOS AUTORAIS
A CONTRATADA emitirá o RRT dos serviços sob sua responsabilidade. O projeto destina-se apenas ao objeto deste contrato, observadas as Leis 9.610/1998 e 12.378/2010.

CLÁUSULA 8 — RESCISÃO E FORO
Na rescisão, são devidos os serviços concluídos e o proporcional da etapa em curso. Fica eleito o foro de [COMARCA].

{{{{data}}}}

_______________________________        _______________________________
{{{{cliente}}}}                         {{{{escritorio}}}}
""",
    }


EMPRESARIAL = _modelo_por_tipo(
    "empresarial", "Projeto empresarial", "sede ou ambiente empresarial",
    "fluxos de equipes, infraestrutura tecnológica, segurança, acústica e continuidade da operação",
)
INSTITUCIONAL = _modelo_por_tipo(
    "institucional", "Projeto institucional", "equipamento de uso coletivo",
    "acessibilidade, segurança, normas setoriais, fluxos de público e validações institucionais",
)
URBANISMO = _modelo_por_tipo(
    "urbanismo", "Projeto de urbanismo", "planejamento e desenho urbano da área de intervenção",
    "legislação urbanística, mobilidade, infraestrutura, meio ambiente, participação e fases de implantação",
)

MODELOS_PADRAO = [PROJETO_ARQUITETONICO, COMERCIAL, EMPRESARIAL, INSTITUCIONAL, URBANISMO]
