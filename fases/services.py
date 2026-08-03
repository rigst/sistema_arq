from django.db import transaction

from tarefas.models import Tarefa


HORAS_USUAIS = {
    "estudo_preliminar": (8, 16, 4),
    "anteprojeto": (24, 16, 8),
    "executivo": (32, 24, 16),
    "comp_estrutural": (12, 20, 16),
    "comp_eletrica": (10, 16, 12),
    "comp_hidraulica": (10, 16, 12),
    "comp_paisagismo": (12, 12, 8),
    "comp_outro": (8, 12, 8),
}


@transaction.atomic
def garantir_tarefas_da_fase(fase, usuario=None):
    """Semeia uma vez; depois, a lista pertence integralmente ao usuário."""
    fase = fase.__class__.objects.select_for_update().get(pk=fase.pk)
    if fase.tarefas_semeadas:
        return fase.tarefas.all()

    estimativas = HORAS_USUAIS.get(fase.chave, ())
    existentes = set(fase.tarefas.values_list("titulo", flat=True))
    novas = []
    for ordem, titulo in enumerate(fase.entrega):
        if titulo in existentes:
            continue
        novas.append(
            Tarefa(
                empresa=fase.empresa,
                criado_por=usuario,
                projeto=fase.projeto,
                fase=fase,
                titulo=titulo,
                prazo=fase.prazo,
                horas_previstas=estimativas[ordem] if ordem < len(estimativas) else 8,
                ordem=ordem,
            )
        )
    Tarefa.objects.bulk_create(novas)
    fase.tarefas_semeadas = True
    fase.save(update_fields=["tarefas_semeadas"])
    return fase.tarefas.all()


def garantir_tarefas_do_projeto(projeto, usuario=None):
    """Disponibiliza o planejamento técnico antes de cada fase ser aberta."""
    comerciais = {"briefing", "proposta", "contrato"}
    for fase in projeto.fases.filter(tarefas_semeadas=False).exclude(status="nao_iniciada").exclude(
        chave__in=comerciais
    ).order_by("ordem", "id"):
        garantir_tarefas_da_fase(fase, usuario)
    return projeto.tarefas.filter(fase__isnull=False)
