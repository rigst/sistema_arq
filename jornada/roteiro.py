"""O roteiro de um projeto novo, do primeiro contato ao contrato assinado.

O sistema tem muitos módulos, e essa é justamente a dificuldade de quem começa
um projeto: saber por onde ir. Aqui a ordem está escrita uma vez só, e cada
etapa sabe dizer se já foi cumprida — o arquiteto segue a linha em vez de
caçar telas no menu.
"""

from dataclasses import dataclass
from typing import Callable

from django.urls import reverse


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
    """As seis etapas de um projeto, na ordem em que acontecem."""
    briefing = getattr(projeto, "briefing", None)
    respostas = briefing.respostas.count() if briefing else 0
    orcamento = projeto.orcamentos.order_by("-criado_em").first()
    proposta = getattr(projeto, "proposta_origem", None)
    contrato = projeto.contratos.order_by("-criado_em").first()
    obra = getattr(projeto, "obra", None)

    return [
        Etapa(
            chave="cliente",
            titulo="Cliente cadastrado",
            descricao="Contato, origem e histórico de conversa.",
            cta="Ver cliente",
            concluida=True,
            url=_url("crm_detalhe", pk=projeto.cliente_id),
            resumo=projeto.cliente.nome,
        ),
        Etapa(
            chave="briefing",
            titulo="Briefing respondido",
            descricao="Rode o roteiro de perguntas com o cliente e registre o que ele quer.",
            cta="Responder briefing",
            concluida=respostas > 0,
            url=_url("briefing_responder", projeto_pk=projeto.pk),
            resumo=f"{respostas} pergunta(s) respondida(s)" if respostas else "",
        ),
        Etapa(
            chave="orcamento",
            titulo="Orçamento de execução",
            descricao="Estime o custo da obra item a item, com fornecedor por item.",
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
            titulo="Proposta de honorários",
            descricao="O que o escritório cobra pelo projeto, calculado da hora técnica.",
            cta="Ver proposta" if proposta else "Criar proposta",
            concluida=proposta is not None,
            url=(
                _url("proposta_detalhe", pk=proposta.pk) if proposta else _url("proposta_nova")
            ),
            resumo=proposta.get_status_display() if proposta else "",
        ),
        Etapa(
            chave="contrato",
            titulo="Contrato assinado",
            descricao="Gere a minuta a partir de um modelo, revise e registre a assinatura.",
            cta="Abrir contrato" if contrato else "Criar contrato",
            concluida=contrato is not None and contrato.status == "ativo",
            url=(
                _url("contrato_detalhe", pk=contrato.pk) if contrato else _url("contrato_novo")
            ),
            resumo=contrato.get_status_display() if contrato else "",
        ),
        Etapa(
            chave="obra",
            titulo="Obra aberta",
            descricao="Cronograma, visitas técnicas e medições que liberam pagamento.",
            cta="Abrir obra" if obra is None else "Acompanhar obra",
            concluida=obra is not None,
            url=(_url("obra_detalhe", pk=obra.pk) if obra else _url("obra_nova")),
            resumo=obra.get_status_display() if obra else "",
        ),
    ]


def proxima_etapa(etapas):
    for etapa in etapas:
        if etapa.pendente:
            return etapa
    return None


def percentual(etapas):
    if not etapas:
        return 0
    return round(100 * sum(1 for e in etapas if e.concluida) / len(etapas))
