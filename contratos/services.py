"""Serviços de contrato: minuta, parcelas e lançamento no financeiro."""

import calendar
from datetime import date
from decimal import Decimal

from django.db import transaction


def _numero(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _moeda(valor):
    return f"R$ {_numero(valor)}"


def _horas(valor):
    return f"{Decimal(valor or 0):.0f}"


def garantir_modelos_padrao(empresa, usuario=None):
    """Disponibiliza as minutas iniciais sem duplicar modelos já instalados."""
    from .modelos_padrao import MODELOS_PADRAO
    from .models import ModeloContrato

    for dados in MODELOS_PADRAO:
        modelo, criado = ModeloContrato.objects.get_or_create(
            empresa=empresa,
            nome=dados["nome"],
            defaults={**dados, "criado_por": usuario},
        )
        if not criado and not modelo.tipo_projeto and dados.get("tipo_projeto"):
            modelo.tipo_projeto = dados["tipo_projeto"]
            modelo.save(update_fields=["tipo_projeto"])
    return ModeloContrato.objects.filter(empresa=empresa, ativo=True)


def contexto_do_contrato(contrato):
    """Dados acumulados desde o cadastro do cliente até a proposta aprovada."""
    from django.utils import timezone
    from propostas.models import Proposta

    projeto = contrato.projeto
    cliente = projeto.cliente
    proposta = None
    if contrato.origem_tipo == "proposta" and contrato.origem_id:
        proposta = Proposta.objects.filter(pk=contrato.origem_id, empresa=contrato.empresa).first()
    if proposta is None:
        proposta = getattr(projeto, "proposta_origem", None)

    fases = list(
        projeto.fases.exclude(chave__in=("briefing", "proposta", "contrato"))
        .order_by("ordem", "id")
    )
    cronograma = "\n".join(
        f"- {fase.nome}: {fase.dias_uteis_proposta} dias úteis"
        if fase.dias_uteis_proposta else f"- {fase.nome}: prazo a definir"
        for fase in fases
    )
    escopo = ""
    if proposta is not None:
        escopo = "\n".join(
            f"- {item.descricao}: {item.inclusoes} — {_horas(item.horas_estimadas)} h — {_moeda(item.valor)}"
            for item in proposta.itens.all()
        )
    endereco = projeto.localizacao
    if projeto.cep:
        endereco = f"{endereco} · CEP {projeto.cep}" if endereco else f"CEP {projeto.cep}"

    return {
        "cliente": cliente.nome,
        "cliente_documento": getattr(cliente, "documento", "") or "",
        "cliente_email": cliente.email,
        "cliente_telefone": cliente.telefone,
        "projeto": projeto.nome,
        "tipo_projeto": projeto.get_tipo_display(),
        "escritorio": contrato.empresa.name,
        "valor": _moeda(contrato.valor_total),
        "horas": _horas(
            proposta.horas_totais if proposta is not None else projeto.horas_estimadas
        ),
        "data": timezone.localdate().strftime("%d/%m/%Y"),
        "data_inicio": projeto.data_inicio.strftime("%d/%m/%Y") if projeto.data_inicio else "",
        "prazo": projeto.data_prevista.strftime("%d/%m/%Y") if projeto.data_prevista else "",
        "cronograma": cronograma,
        "escopo": escopo,
        "endereco": endereco,
        "area_terreno": _numero(projeto.area_terreno) if projeto.area_terreno else "",
        "area_construida": _numero(projeto.area_construida) if projeto.area_construida else "",
    }


@transaction.atomic
def criar_contrato_da_proposta(proposta, usuario):
    """Cria uma única minuta a partir da proposta e abre com texto preenchido."""
    from .models import Contrato

    projeto = proposta.projeto_gerado
    prazos = list(
        projeto.fases.exclude(chave__in=("briefing", "proposta", "contrato"))
        .exclude(prazo__isnull=True)
        .values_list("prazo", flat=True)
    )
    projeto.valor_contratado = proposta.valor_total
    projeto.horas_estimadas = proposta.horas_totais
    if projeto.data_inicio is None:
        from django.utils import timezone

        projeto.data_inicio = timezone.localdate()
    if prazos:
        projeto.data_prevista = max(prazos)
    projeto.save(
        update_fields=["valor_contratado", "horas_estimadas", "data_inicio", "data_prevista"]
    )

    contrato, criado = Contrato.objects.get_or_create(
        empresa=proposta.empresa,
        projeto=projeto,
        origem_tipo="proposta",
        origem_id=proposta.pk,
        defaults={
            "criado_por": usuario,
            "titulo": f"Contrato — {projeto.nome}",
            "valor_total": proposta.valor_total,
        },
    )
    if not criado:
        return contrato

    modelos = garantir_modelos_padrao(proposta.empresa, usuario)
    modelo = (
        modelos.filter(tipo_projeto=projeto.tipo).first()
        or modelos.filter(tipo_projeto="", padrao=True).first()
        or modelos.first()
    )
    if modelo is not None:
        contrato.corpo = modelo.gerar(contexto_do_contrato(contrato))
        contrato.save(update_fields=["corpo"])
    return contrato


def _vencimento_mensal(primeira_data, meses):
    indice = primeira_data.month - 1 + meses
    ano = primeira_data.year + indice // 12
    mes = indice % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(primeira_data.day, ultimo_dia))


def gerar_parcelas(contrato, quantidade, primeira_data, intervalo_dias=None):
    """Cria parcelas mensais, preservando o dia do primeiro vencimento."""
    from .models import Parcela

    contrato.parcelas.all().delete()
    quantidade = max(int(quantidade), 1)
    total = Decimal(contrato.valor_total or 0) + sum(
        (alteracao.valor_delta for alteracao in contrato.alteracoes.all()), Decimal("0")
    )
    base = (total / quantidade).quantize(Decimal("0.01"))
    parcelas = []
    acumulado = Decimal("0")
    for i in range(quantidade):
        # Última parcela ajusta o arredondamento.
        valor = total - acumulado if i == quantidade - 1 else base
        acumulado += valor
        parcelas.append(
            Parcela(
                empresa=contrato.empresa,
                contrato=contrato,
                numero=i + 1,
                valor=valor,
                vencimento=_vencimento_mensal(primeira_data, i),
            )
        )
    Parcela.objects.bulk_create(parcelas)


@transaction.atomic
def lancar_parcelas_no_financeiro(contrato, conta):
    """Cria um lançamento (entrada, previsto) para cada parcela ainda não lançada.
    Idempotente via contrato.parcelas_lancadas."""
    from financeiro.models import Lancamento

    if contrato.parcelas_lancadas or conta is None:
        return 0
    criados = 0
    for parcela in contrato.parcelas.filter(lancamento__isnull=True):
        lanc = Lancamento.objects.create(
            empresa=contrato.empresa,
            conta=conta,
            tipo="entrada",
            projeto=contrato.projeto,
            descricao=f"{contrato.titulo} — parcela {parcela.numero}",
            valor=parcela.valor,
            data=parcela.vencimento,
            status="previsto",
            origem_tipo="parcela",
            origem_id=parcela.pk,
        )
        parcela.lancamento = lanc
        parcela.save(update_fields=["lancamento"])
        criados += 1
    contrato.parcelas_lancadas = True
    contrato.save(update_fields=["parcelas_lancadas"])
    return criados
