"""Implantação guiada: 5 etapas sequenciais. O progresso é derivado dos dados
reais do tenant — cada etapa entrega uma área funcionando antes da próxima."""

from core.tenancy import queryset_da_empresa


def montar_checklist(user):
    from crm.models import Cliente
    from financeiro.models import ContaBancaria
    from precificacao.models import CustoFixo
    from projetos.models import Projeto
    from tarefas.models import Tarefa

    def existe(model):
        return queryset_da_empresa(model.objects.all(), user).exists()

    etapas = [
        {
            "ordem": 1,
            "titulo": "Base administrativa",
            "descricao": "Cadastre seu primeiro cliente para começar a carteira.",
            "concluida": existe(Cliente),
            "url_nome": "crm_novo",
            "cta": "Cadastrar cliente",
        },
        {
            "ordem": 2,
            "titulo": "Motor de precificação",
            "descricao": "Lance seus custos fixos para o sistema calcular a hora técnica.",
            "concluida": existe(CustoFixo),
            "url_nome": "precificacao",
            "cta": "Configurar custos",
        },
        {
            "ordem": 3,
            "titulo": "Controle financeiro",
            "descricao": "Crie uma conta para registrar entradas, saídas e saldos.",
            "concluida": existe(ContaBancaria),
            "url_nome": "financeiro_painel",
            "cta": "Criar conta",
        },
        {
            "ordem": 4,
            "titulo": "Estrutura de projetos",
            "descricao": "Abra um projeto (com etapas) — direto ou aprovando uma proposta.",
            "concluida": existe(Projeto),
            "url_nome": "projeto_novo",
            "cta": "Criar projeto",
        },
        {
            "ordem": 5,
            "titulo": "Operação diária",
            "descricao": "Delegue a primeira tarefa com responsável e prazo.",
            "concluida": existe(Tarefa),
            "url_nome": "tarefas_lista",
            "cta": "Criar tarefa",
        },
    ]

    concluidas = sum(1 for e in etapas if e["concluida"])
    # A próxima etapa a fazer é a primeira ainda não concluída.
    proxima = next((e for e in etapas if not e["concluida"]), None)
    if proxima:
        proxima["atual"] = True

    return {
        "etapas": etapas,
        "concluidas": concluidas,
        "total": len(etapas),
        "percentual": round(concluidas / len(etapas) * 100),
        "completo": concluidas == len(etapas),
    }
