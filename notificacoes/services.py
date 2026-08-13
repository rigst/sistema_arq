"""Motor de alertas: varre prazos, projetos parados, desvios de obra e
obrigações regulatórias, criando notificações (dedup por chave)."""

from datetime import timedelta

from django.utils import timezone

# Limiares
DIAS_PROJETO_PARADO = 14
DIAS_TAREFA_PROXIMA = 3


def _emitir(grupo, chave, titulo, mensagem, nivel="alerta", url=""):
    """Cria a notificação se ainda não existir uma não-lida com a mesma chave."""
    from .models import Notificacao

    _obj, criado = Notificacao.objects.get_or_create(
        empresa=grupo,
        chave=chave,
        lida=False,
        defaults={"titulo": titulo, "mensagem": mensagem, "nivel": nivel, "url": url},
    )
    return 1 if criado else 0


def varrer_empresa(grupo):
    """Varre uma empresa (Group) e emite notificações. Retorna quantas criou.

    Cada fonte de alerta vive numa função própria: são quatro varreduras
    independentes, e juntas numa só o corpo passava de qualquer limite de
    complexidade que se queira usar.
    """
    return (
        _alertar_tarefas(grupo)
        + _alertar_projetos_parados(grupo)
        + _alertar_obras_em_desvio(grupo)
        + _alertar_obrigacoes(grupo)
    )


def _alertar_tarefas(grupo):
    """Tarefas com prazo vencido ou próximo."""
    from django.urls import reverse

    from tarefas.models import Tarefa

    hoje = timezone.localdate()
    criadas = 0
    limite = hoje + timedelta(days=DIAS_TAREFA_PROXIMA)
    tarefas = Tarefa.objects.filter(empresa=grupo, prazo__isnull=False, prazo__lte=limite).exclude(
        status="concluida"
    )
    for t in tarefas:
        # O `is not None` repete a garantia do prazo__isnull=False acima: o
        # filtro está no queryset, longe daqui, e não acompanha o item.
        atrasada = t.prazo is not None and t.prazo < hoje
        criadas += _emitir(
            grupo,
            chave=f"tarefa-prazo-{t.pk}",
            titulo=f"Tarefa {'atrasada' if atrasada else 'no prazo'}: {t.titulo}",
            mensagem=f"Prazo {t.prazo:%d/%m/%Y}.",
            nivel="critico" if atrasada else "alerta",
            url=reverse("projetos_painel"),
        )
    return criadas


def _alertar_projetos_parados(grupo):
    """Projetos ativos sem atualização há muito tempo."""
    from django.urls import reverse

    from projetos.models import Projeto

    criadas = 0
    corte = timezone.now() - timedelta(days=DIAS_PROJETO_PARADO)
    projetos = Projeto.objects.filter(empresa=grupo, status="ativo", ultima_atualizacao__lt=corte)
    for p in projetos:
        criadas += _emitir(
            grupo,
            chave=f"projeto-parado-{p.pk}",
            titulo=f"Projeto parado: {p.nome}",
            mensagem=f"Sem atualização há {p.dias_parado} dias.",
            nivel="alerta",
            url=reverse("projeto_detalhe", args=[p.pk]),
        )
    return criadas


def _alertar_obras_em_desvio(grupo):
    """Obras cujo avanço real ficou para trás do previsto."""
    from django.urls import reverse

    from obras.models import Obra

    criadas = 0
    for obra in Obra.objects.filter(empresa=grupo).prefetch_related("etapas"):
        if obra.em_desvio:
            criadas += _emitir(
                grupo,
                chave=f"obra-desvio-{obra.pk}",
                titulo=f"Obra atrasada: {obra.projeto.nome}",
                mensagem=f"Desvio de {obra.desvio} p.p. frente ao previsto.",
                nivel="alerta",
                url=reverse("obra_detalhe", args=[obra.pk]),
            )
    return criadas


def _alertar_obrigacoes(grupo):
    """Obrigações regulatórias vencidas, vencendo ou pendentes de registro."""
    from django.urls import reverse

    from regulatorio.models import ObrigacaoTecnica

    criadas = 0
    for o in ObrigacaoTecnica.objects.filter(empresa=grupo).exclude(status="baixada"):
        if o.vencida:
            estado, nivel, msg = "vencida", "critico", f"Venceu em {o.vencimento:%d/%m/%Y}."
        elif o.vencendo:
            estado, nivel, msg = "vencendo", "alerta", f"Vence em {o.dias_para_vencer} dias."
        elif o.pendente_registro:
            estado, nivel, msg = "pendente", "alerta", "Registro ainda pendente."
        else:
            continue
        criadas += _emitir(
            grupo,
            chave=f"obrigacao-{o.pk}-{estado}",
            titulo=f"{o.get_tipo_display()} {estado}",
            mensagem=msg,
            nivel=nivel,
            url=reverse("regulatorio_lista"),
        )

    return criadas


def varrer_todas():
    """Varre todas as empresas reais (ignora grupos de visitante)."""
    from django.contrib.auth.models import Group

    from core.tenancy import VISITOR_GROUP_PREFIX

    total = 0
    grupos = Group.objects.filter(empresa_registro__isnull=False).exclude(
        name__startswith=VISITOR_GROUP_PREFIX
    )
    for grupo in grupos:
        total += varrer_empresa(grupo)
    return total
