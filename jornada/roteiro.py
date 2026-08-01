"""O roteiro de um projeto novo, do primeiro contato ao contrato assinado.

O sistema tem muitos módulos, e essa é justamente a dificuldade de quem começa
um projeto: saber por onde ir. Aqui a ordem está escrita uma vez só, e cada
etapa sabe dizer se já foi cumprida — o arquiteto segue a linha em vez de
caçar telas no menu.
"""

from dataclasses import dataclass
from typing import Callable

from django.urls import reverse

from core.contexto import com_projeto


@dataclass
class Etapa:
    chave: str
    titulo: str
    descricao: str
    cta: str
    concluida: bool
    url: str
    resumo: str = ""

    @property
    def pendente(self):
        return not self.concluida


def _url(nome, **kwargs):
    return reverse(nome, kwargs=kwargs) if kwargs else reverse(nome)


def montar_roteiro(projeto):
    """As etapas de um projeto, na ordem em que acontecem de verdade.

    Briefing antes de orçamento porque não se orça o que ainda não foi definido;
    orçamento antes de proposta porque a proposta cobra em cima de um custo
    conhecido; contrato antes de começar a desenhar. A execução só entra na
    lista quando o escritório acompanha a obra — que é a minoria dos trabalhos.
    """
    briefing = getattr(projeto, "briefing", None)
    respostas = briefing.respostas.count() if briefing else 0
    orcamento = projeto.orcamentos.order_by("-criado_em").first()
    proposta = getattr(projeto, "proposta_origem", None)
    contrato = projeto.contratos.order_by("-criado_em").first()
    obra = getattr(projeto, "obra", None)
    tarefas_abertas = projeto.tarefas.exclude(status="concluida").count()
    tarefas_total = projeto.tarefas.count()
    etapas_feitas = projeto.etapas.filter(status="concluida").count()
    etapas_total = projeto.etapas.count()

    etapas = [
        Etapa(
            chave="cliente",
            titulo="Cliente",
            descricao="Contato, origem e histórico de conversa.",
            cta="Ver cliente",
            concluida=True,
            url=_url("crm_detalhe", pk=projeto.cliente_id),
            resumo=projeto.cliente.nome,
        ),
        Etapa(
            chave="briefing",
            titulo="Briefing",
            descricao="Rode o roteiro de perguntas com o cliente e registre o que ele quer.",
            cta="Responder briefing",
            concluida=respostas > 0,
            url=_url("briefing_responder", projeto_pk=projeto.pk),
            resumo=f"{respostas} resposta(s)" if respostas else "",
        ),
        Etapa(
            chave="orcamento",
            titulo="Orçamento",
            descricao="Quanto custa executar, item a item — a base para saber o que cobrar.",
            cta="Montar orçamento" if orcamento is None else "Abrir orçamento",
            concluida=orcamento is not None and orcamento.itens.exists(),
            url=(
                _url("orcamento_detalhe", pk=orcamento.pk)
                if orcamento
                else _url("orcamento_novo", projeto_pk=projeto.pk)
            ),
            resumo=f"v{orcamento.versao} · R$ {orcamento.total}" if orcamento else "",
        ),
        Etapa(
            chave="proposta",
            titulo="Proposta",
            descricao="O que o escritório cobra pelo projeto, calculado da hora técnica.",
            cta="Ver proposta" if proposta else "Criar proposta",
            concluida=proposta is not None,
            url=(
                _url("proposta_detalhe", pk=proposta.pk)
                if proposta
                else com_projeto(_url("proposta_nova"), projeto)
            ),
            resumo=proposta.get_status_display() if proposta else "",
        ),
        Etapa(
            chave="contrato",
            titulo="Contrato",
            descricao="Gere a minuta a partir de um modelo, revise e registre a assinatura.",
            cta="Abrir contrato" if contrato else "Criar contrato",
            concluida=contrato is not None and contrato.status == "ativo",
            url=(
                _url("contrato_detalhe", pk=contrato.pk)
                if contrato
                else com_projeto(_url("contrato_novo"), projeto)
            ),
            resumo=contrato.get_status_display() if contrato else "",
        ),
        Etapa(
            chave="elaboracao",
            titulo="Elaboração",
            descricao="As disciplinas e as etapas de prancha: é aqui que o projeto é feito.",
            cta="Ver elaboração",
            concluida=etapas_total > 0 and etapas_feitas == etapas_total,
            url=f"{_url('projeto_detalhe', pk=projeto.pk)}#elaboracao",
            resumo=(
                f"{etapas_feitas}/{etapas_total} etapas"
                + (f" · {tarefas_abertas} tarefa(s) aberta(s)" if tarefas_abertas else "")
                if etapas_total
                else (f"{tarefas_total} tarefa(s)" if tarefas_total else "")
            ),
        ),
    ]

    # A execução é opcional e por isso entra por último e só quando marcada.
    if projeto.tem_execucao:
        etapas.append(
            Etapa(
                chave="execucao",
                titulo="Execução",
                descricao="Cronograma de obra, visitas técnicas e medições que liberam pagamento.",
                cta="Abrir execução" if obra is None else "Acompanhar execução",
                concluida=obra is not None and obra.status == "concluida",
                url=(
                    _url("obra_detalhe", pk=obra.pk)
                    if obra
                    else com_projeto(_url("obra_nova"), projeto)
                ),
                resumo=obra.get_status_display() if obra else "",
            )
        )

    return etapas


def proxima_etapa(etapas):
    for etapa in etapas:
        if etapa.pendente:
            return etapa
    return None


def percentual(etapas):
    if not etapas:
        return 0
    return round(100 * sum(1 for e in etapas if e.concluida) / len(etapas))
