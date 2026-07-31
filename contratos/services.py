"""Serviços de contrato: geração de parcelas e lançamento no financeiro."""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction


def gerar_parcelas(contrato, quantidade, primeira_data, intervalo_dias=30):
    """Cria N parcelas iguais a partir do valor total do contrato."""
    from .models import Parcela

    contrato.parcelas.all().delete()
    quantidade = max(int(quantidade), 1)
    total = Decimal(contrato.valor_total or 0)
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
                vencimento=primeira_data + timedelta(days=intervalo_dias * i),
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
