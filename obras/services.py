"""Serviços de obra: aprovação de medição libera pagamento no financeiro."""

from django.db import transaction


@transaction.atomic
def aprovar_medicao(medicao, conta):
    """Aprova a medição e cria um lançamento (entrada, previsto) no financeiro,
    vinculado ao projeto da obra. Idempotente: não relança se já houver lançamento."""
    from financeiro.models import Lancamento

    if medicao.aprovada and medicao.lancamento_id:
        return None
    if conta is None:
        return None

    projeto = medicao.etapa.obra.projeto
    lanc = Lancamento.objects.create(
        empresa=medicao.empresa,
        conta=conta,
        tipo="entrada",
        projeto=projeto,
        descricao=f"Medição {medicao.etapa.nome} — {medicao.percentual_medido}%",
        valor=medicao.valor_liberado,
        data=medicao.data,
        status="previsto",
        origem_tipo="medicao",
        origem_id=medicao.pk,
    )
    medicao.aprovada = True
    medicao.lancamento = lanc
    medicao.save(update_fields=["aprovada", "lancamento"])
    # Puxa o avanço real da etapa para o medido, se maior.
    etapa = medicao.etapa
    if medicao.percentual_medido > etapa.percentual_real:
        etapa.percentual_real = medicao.percentual_medido
        etapa.save(update_fields=["percentual_real"])
    return lanc
