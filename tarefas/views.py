from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import TarefaForm
from .models import ApontamentoHora, Tarefa


@login_required
def lista_tarefas(request):
    tarefas = queryset_da_empresa(
        Tarefa.objects.select_related("projeto", "responsavel", "fornecedor"), request.user
    )
    projeto = projeto_do_pedido(request)
    if projeto is not None:
        tarefas = tarefas.filter(projeto=projeto)

    if request.method == "POST":
        form = TarefaForm(request.POST, user=request.user, projeto=projeto)
        if form.is_valid():
            tarefa = form.save(commit=False)
            tarefa.empresa = obter_grupo_empresa_ou_erro(request.user)
            tarefa.criado_por = request.user
            if projeto is not None:
                tarefa.projeto = projeto
            tarefa.save()
            messages.success(request, "Tarefa criada.")
            destino = reverse("tarefas_lista")
            return redirect(f"{destino}?projeto={projeto.pk}" if projeto else destino)
        messages.error(request, "Confira os campos da tarefa.")
    else:
        form = TarefaForm(user=request.user, projeto=projeto)

    timer_ativo = (
        queryset_da_empresa(ApontamentoHora.objects.all(), request.user)
        .filter(usuario=request.user, fim__isnull=True)
        .select_related("projeto", "tarefa")
        .first()
    )
    return render(
        request,
        "tarefas/lista.html",
        {"tarefas": tarefas, "form": form, "timer_ativo": timer_ativo, "projeto": projeto},
    )


@require_POST
@login_required
def concluir_tarefa(request, pk):
    tarefa = get_object_or_404(queryset_da_empresa(Tarefa.objects.all(), request.user), pk=pk)
    tarefa.status = "concluida" if tarefa.status != "concluida" else "aberta"
    tarefa.save(update_fields=["status"])
    return redirect("tarefas_lista")


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
    return redirect("tarefas_lista")


@require_POST
@login_required
def parar_timer(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    ApontamentoHora.objects.filter(empresa=grupo, usuario=request.user, fim__isnull=True).update(
        fim=timezone.now()
    )
    messages.success(request, "Tempo registrado.")
    return redirect("tarefas_lista")
