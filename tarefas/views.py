from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import ApontamentoForm


def _de_onde_veio(request):
    """Volta para a tela que disparou a ação.

    Concluir tarefa e cronômetro agora acontecem de dentro da fase, e mandar
    para uma lista global depois disso perderia o lugar. O Referer é validado
    contra o próprio host: sem isso, um link de fora conseguiria escolher para
    onde a pessoa vai parar depois de uma ação autenticada.
    """
    from django.utils.http import url_has_allowed_host_and_scheme

    destino = request.META.get("HTTP_REFERER", "")
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destino
    return "dashboard"
from .models import ApontamentoHora, Tarefa


@require_POST
@login_required
def concluir_tarefa(request, pk):
    tarefa = get_object_or_404(queryset_da_empresa(Tarefa.objects.all(), request.user), pk=pk)
    if tarefa.fase_id and tarefa.fase.bloqueada:
        messages.error(request, "Esta tarefa pertence a uma fase ainda bloqueada.")
        return redirect(_de_onde_veio(request))
    tarefa.status = "concluida" if tarefa.status != "concluida" else "aberta"
    tarefa.save(update_fields=["status"])
    return redirect(_de_onde_veio(request))


def cronometro_aberto(user):
    """O apontamento em aberto do usuário — rodando ou pausado.

    Um por vez, de propósito: dois relógios andando juntos fazem a mesma hora
    ser cobrada duas vezes.
    """
    grupo = obter_grupo_empresa_usuario_ou_none(user)
    if grupo is None:
        return None
    return (
        ApontamentoHora.objects.filter(empresa=grupo, usuario=user, fim__isnull=True)
        .select_related("projeto")
        .first()
    )


def obter_grupo_empresa_usuario_ou_none(user):
    from core.tenancy import obter_grupo_empresa_usuario

    if not user.is_authenticated:
        return None
    return obter_grupo_empresa_usuario(user)


@require_POST
@login_required
def iniciar_timer(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    # Fecha qualquer relógio aberto antes de abrir outro, contando as pausas.
    for aberto in ApontamentoHora.objects.filter(
        empresa=grupo, usuario=request.user, fim__isnull=True
    ):
        aberto.parar()

    tarefa = None
    tarefa_id = request.POST.get("tarefa")
    if tarefa_id:
        tarefa = queryset_da_empresa(Tarefa.objects.all(), request.user).filter(pk=tarefa_id).first()

    projeto = None
    projeto_id = request.POST.get("projeto")
    if projeto_id:
        from projetos.models import Projeto

        projeto = queryset_da_empresa(Projeto.objects.all(), request.user).filter(pk=projeto_id).first()

    descricao = request.POST.get("descricao", "").strip()
    if not descricao:
        messages.error(request, "Diga o que vai fazer antes de começar a contar.")
        return redirect(_de_onde_veio(request))

    ApontamentoHora.objects.create(
        empresa=grupo,
        usuario=request.user,
        tarefa=tarefa,
        projeto=projeto or (tarefa.projeto if tarefa else None),
        descricao=descricao,
    )
    messages.success(request, f"Cronômetro rodando: {descricao}.")
    return redirect(_de_onde_veio(request))


@require_POST
@login_required
def pausar_timer(request):
    aberto = cronometro_aberto(request.user)
    if aberto is None:
        messages.info(request, "Nenhum cronômetro em andamento.")
    elif aberto.pausado:
        aberto.retomar()
        messages.success(request, f"Cronômetro retomado: {aberto.descricao}.")
    else:
        aberto.pausar()
        messages.success(request, f"Cronômetro pausado em {aberto.horas} h.")
    return redirect(_de_onde_veio(request))


@require_POST
@login_required
def parar_timer(request):
    aberto = cronometro_aberto(request.user)
    if aberto is None:
        messages.info(request, "Nenhum cronômetro em andamento.")
        return redirect(_de_onde_veio(request))
    aberto.parar()
    if aberto.horas <= 0:
        # Zero hora não é registro, é ruído na tabela do projeto.
        aberto.delete()
        messages.info(request, "Cronômetro parado antes de contar um minuto; nada registrado.")
    else:
        messages.success(request, f"{aberto.horas} h registradas: {aberto.descricao}.")
    return redirect(_de_onde_veio(request))


@require_POST
@login_required
def apontar_hora(request, projeto_pk):
    """Lançamento à mão, para o que não passou pelo cronômetro."""
    from projetos.models import Projeto

    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.all(), request.user), pk=projeto_pk
    )
    form = ApontamentoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Informe o que foi feito e quantas horas.")
        return redirect("projeto_detalhe", pk=projeto.pk)

    horas = form.cleaned_data["horas"]
    agora = timezone.now()
    ApontamentoHora.objects.create(
        empresa=projeto.empresa,
        usuario=request.user,
        projeto=projeto,
        descricao=form.cleaned_data["descricao"],
        inicio=agora - timedelta(hours=float(horas)),
        fim=agora,
    )
    messages.success(request, f"{horas} h lançadas em {projeto.nome}.")
    return redirect("projeto_detalhe", pk=projeto.pk)


@require_POST
@login_required
def editar_apontamento(request, pk):
    apontamento = get_object_or_404(
        queryset_da_empresa(ApontamentoHora.objects.select_related("projeto"), request.user), pk=pk
    )
    if apontamento.em_andamento:
        messages.error(request, "Pare o cronômetro antes de corrigir o registro.")
        return redirect("projeto_detalhe", pk=apontamento.projeto_id)

    form = ApontamentoForm(request.POST)
    if form.is_valid():
        # Editar horas move o início: o fim é quando o trabalho acabou, e é o
        # que ancora o registro no dia certo da lista.
        apontamento.descricao = form.cleaned_data["descricao"]
        apontamento.segundos_pausa = 0
        apontamento.inicio = apontamento.fim - timedelta(hours=float(form.cleaned_data["horas"]))
        apontamento.save(update_fields=["descricao", "inicio", "segundos_pausa"])
        messages.success(request, "Registro de horas atualizado.")
    else:
        messages.error(request, "Informe o que foi feito e quantas horas.")
    return redirect("projeto_detalhe", pk=apontamento.projeto_id)


@require_POST
@login_required
def remover_apontamento(request, pk):
    apontamento = get_object_or_404(
        queryset_da_empresa(ApontamentoHora.objects.all(), request.user), pk=pk
    )
    projeto_pk = apontamento.projeto_id
    apontamento.delete()
    messages.success(request, "Registro de horas removido.")
    if projeto_pk:
        return redirect("projeto_detalhe", pk=projeto_pk)
    return redirect(_de_onde_veio(request))
