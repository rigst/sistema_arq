from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import TarefaForm


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
    tarefa.status = "concluida" if tarefa.status != "concluida" else "aberta"
    tarefa.save(update_fields=["status"])
    return redirect(_de_onde_veio(request))


@require_POST
@login_required
def iniciar_timer(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    # Fecha qualquer timer aberto do usuário antes de abrir outro.
    ApontamentoHora.objects.filter(empresa=grupo, usuario=request.user, fim__isnull=True).update(
        fim=timezone.now()
    )
    tarefa = None
    tarefa_id = request.POST.get("tarefa")
    if tarefa_id:
        tarefa = queryset_da_empresa(Tarefa.objects.all(), request.user).filter(pk=tarefa_id).first()
    ApontamentoHora.objects.create(
        empresa=grupo,
        usuario=request.user,
        tarefa=tarefa,
        projeto=tarefa.projeto if tarefa else None,
        descricao=request.POST.get("descricao", ""),
    )
    return redirect(_de_onde_veio(request))


@require_POST
@login_required
def parar_timer(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    ApontamentoHora.objects.filter(empresa=grupo, usuario=request.user, fim__isnull=True).update(
        fim=timezone.now()
    )
    messages.success(request, "Tempo registrado.")
    return redirect(_de_onde_veio(request))
