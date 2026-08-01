"""O roteiro do projeto, montado a partir das fases reais.

A ordem não mora mais aqui: mora em fases/catalogo.py, e as fases de cada
projeto são registros no banco com status próprio. Este módulo só traduz isso
para o que a interface precisa mostrar — onde clicar agora e o que já foi feito.

Antes o roteiro inferia o progresso olhando de longe (existe orçamento? existe
contrato?). Inferir era frágil e não guardava nada: não dava para saber quando
o cliente aprovou o estudo preliminar, nem qual versão ele viu.
"""

from dataclasses import dataclass

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
    status: str = ""
    liberada: bool = True

    @property
    def pendente(self):
        return not self.concluida


_CTA_POR_STATUS = {
    "nao_iniciada": "Começar",
    "em_elaboracao": "Continuar",
    "aguardando_cliente": "Aguardando cliente",
    "ajustes": "Retomar ajustes",
    "aprovada": "Ver fase",
}

_RESUMO_POR_STATUS = {
    "nao_iniciada": "não iniciada",
    "em_elaboracao": "em elaboração",
    "aguardando_cliente": "com o cliente",
    "ajustes": "ajustes pedidos",
    "aprovada": "aprovada",
}


def montar_roteiro(projeto):
    """As fases do projeto na ordem, prontas para desenhar a trilha."""
    etapas = []
    for fase in projeto.fases.all():
        n_arquivos = fase.arquivos.count()
        resumo = _RESUMO_POR_STATUS.get(fase.status, fase.status)
        if n_arquivos:
            resumo = f"{resumo} · {n_arquivos} arq."
        etapas.append(
            Etapa(
                chave=fase.chave,
                titulo=fase.nome,
                descricao=fase.resumo,
                cta=_CTA_POR_STATUS.get(fase.status, "Abrir"),
                concluida=fase.status == "aprovada",
                url=reverse("fase_detalhe", kwargs={"pk": fase.pk}),
                resumo=resumo,
                status=fase.status,
                liberada=fase.liberada,
            )
        )

    # A execução da obra é uma seção à parte e ainda não implementada por
    # inteiro. Entra no fim da trilha só para quem acompanha obra, e como
    # ponteiro para a seção — não como fase de projeto.
    if projeto.tem_execucao:
        obra = getattr(projeto, "obra", None)
        etapas.append(
            Etapa(
                chave="execucao",
                titulo="Execução",
                descricao="Acompanhamento de obra — seção à parte, em construção.",
                cta="Acompanhar execução" if obra else "Abrir execução",
                concluida=obra is not None and obra.status == "concluida",
                url=(
                    reverse("obra_detalhe", kwargs={"pk": obra.pk})
                    if obra
                    else f"{reverse('obra_nova')}?projeto={projeto.pk}"
                ),
                resumo=obra.get_status_display().lower() if obra else "não aberta",
                status="obra",
            )
        )
    return etapas


def proxima_etapa(etapas):
    """A fase em que se deve trabalhar agora.

    Prioriza o que já está aberto: uma fase em elaboração pede mais atenção do
    que a seguinte, que nem começou.
    """
    em_curso = [e for e in etapas if e.status in ("em_elaboracao", "ajustes")]
    if em_curso:
        return em_curso[0]
    for etapa in etapas:
        if etapa.pendente:
            return etapa
    return None


def percentual(etapas):
    if not etapas:
        return 0
    return round(100 * sum(1 for e in etapas if e.concluida) / len(etapas))
