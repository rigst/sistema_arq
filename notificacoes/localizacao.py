"""De que tela veio o aviso, em português.

O histórico guarda "Tarefa criada." — que três dias depois não diz nada. Falta
o lugar. Resolver o nome da rota dá isso de graça e sem tocar em nenhuma view:
o Django já sabe qual view atendeu a requisição.

Quando a rota carrega o objeto (uma fase, um projeto), o nome do objeto entra
junto — é a diferença entre "em Fases" e "em Estudo preliminar · Casa Ipê".
"""

import logging

logger = logging.getLogger(__name__)

# Nome da rota → como a pessoa chama aquela tela.
POR_ROTA = {
    "dashboard": "Painel",
    "projetos_painel": "Projetos",
    "projeto_detalhe": "Projeto",
    "projeto_novo": "Novo projeto",
    "projeto_editar": "Edição do projeto",
    "jornada_abrir": "Novo projeto",
    "fase_detalhe": "Fase",
    "fase_iniciar": "Fase",
    "fase_enviar": "Fase",
    "fase_responder": "Fase",
    "fase_concluir": "Fase",
    "fase_ajustar": "Fase",
    "fase_anexar": "Arquivos da fase",
    "fase_comentar": "Lembretes",
    "fase_nova_tarefa": "Tarefas da fase",
    "fase_editar_complementares": "Fases do projeto",
    "fase_ativar_complementar": "Fases do projeto",
    "fase_arquivo_editar": "Arquivos da fase",
    "fase_arquivo_remover": "Arquivos da fase",
    "lembrete_editar": "Lembretes",
    "lembrete_remover": "Lembretes",
    "projeto_lembrete": "Lembretes do projeto",
    "briefing_responder": "Briefing",
    "briefing_salvar_blocos": "Briefing",
    "briefing_add_ambiente": "Programa de necessidades",
    "briefing_templates": "Modelos de briefing",
    "briefing_template_detalhe": "Modelo de briefing",
    "tarefa_concluir": "Tarefas",
    "timer_iniciar": "Cronômetro",
    "timer_parar": "Cronômetro",
    "agenda": "Agenda",
    "agenda_remover": "Agenda",
    "crm_lista": "Clientes",
    "crm_detalhe": "Cliente",
    "crm_novo": "Clientes",
    "crm_editar": "Cliente",
    "obras_lista": "Execução",
    "obra_detalhe": "Execução",
    "obra_nova": "Execução",
    "orcamentos_lista": "Orçamentos",
    "orcamento_detalhe": "Orçamento",
    "propostas_lista": "Propostas",
    "proposta_detalhe": "Proposta",
    "contratos_lista": "Contratos",
    "contrato_detalhe": "Contrato",
    "contratos_modelos": "Modelos de contrato",
    "arquivos_lista": "Arquivos",
    "financeiro_painel": "Financeiro",
    "precificacao": "Hora técnica",
    "regulatorio_lista": "Regulatório",
    "fornecedores_lista": "Fornecedores",
    "identidade": "Identidade do escritório",
    "modelos": "Modelos",
    "notificacoes_lista": "Notificações",
}

# Rotas cujo pk aponta para um objeto com nome útil. (rota → app.Model)
OBJETO_POR_ROTA = {
    "fase_detalhe": ("fases", "Fase"),
    "fase_iniciar": ("fases", "Fase"),
    "fase_enviar": ("fases", "Fase"),
    "fase_responder": ("fases", "Fase"),
    "fase_concluir": ("fases", "Fase"),
    "fase_ajustar": ("fases", "Fase"),
    "fase_anexar": ("fases", "Fase"),
    "fase_comentar": ("fases", "Fase"),
    "fase_nova_tarefa": ("fases", "Fase"),
    "projeto_detalhe": ("projetos", "Projeto"),
    "projeto_editar": ("projetos", "Projeto"),
}


def descrever(request):
    """(onde, url) da tela que gerou o aviso."""
    rota = getattr(request, "resolver_match", None)
    if rota is None:
        return "", ""

    nome = rota.url_name or ""
    onde = POR_ROTA.get(nome, "")
    detalhe = _nome_do_objeto(nome, rota.kwargs)
    if detalhe:
        onde = f"{onde} · {detalhe}" if onde else detalhe
    return onde, request.path


def _nome_do_objeto(nome_rota, kwargs):
    alvo = OBJETO_POR_ROTA.get(nome_rota)
    pk = kwargs.get("pk") or kwargs.get("projeto_pk")
    if alvo is None or not pk:
        return ""
    try:
        from django.apps import apps

        objeto = apps.get_model(*alvo).objects.filter(pk=pk).first()
        return str(objeto) if objeto else ""
    except Exception:
        logger.debug("Não foi possível nomear o objeto do aviso.", exc_info=True)
        return ""
