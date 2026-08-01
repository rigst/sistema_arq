from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import ObrigacaoTecnicaForm
from .models import ObrigacaoTecnica


@login_required
def lista_obrigacoes(request):
    obrigacoes = queryset_da_empresa(
        ObrigacaoTecnica.objects.select_related("projeto"), request.user
    )
    tipo = request.GET.get("tipo", "")
    if tipo:
        obrigacoes = obrigacoes.filter(tipo=tipo)
    projeto = projeto_do_pedido(request)
    if projeto is not None:
        obrigacoes = obrigacoes.filter(projeto=projeto)
    obrigacoes = list(obrigacoes)
    alertas = [o for o in obrigacoes if o.vencida or o.vencendo or o.pendente_registro]
    return render(
        request,
        "regulatorio/lista.html",
        {
            "obrigacoes": obrigacoes,
            "alertas": alertas,
            "tipo_ativo": tipo,
            "tipo_choices": ObrigacaoTecnica.TIPO_CHOICES,
            "projeto": projeto,
        },
    )


@login_required
def nova_obrigacao(request):
    if request.method == "POST":
        form = ObrigacaoTecnicaForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            obrigacao = form.save(commit=False)
            obrigacao.empresa = obter_grupo_empresa_ou_erro(request.user)
            obrigacao.criado_por = request.user
            obrigacao.save()
            messages.success(request, "Obrigação registrada.")
            return redirect("regulatorio_lista")
    else:
        form = ObrigacaoTecnicaForm(user=request.user)
    return render(
        request, "regulatorio/form.html", {"form": form, "titulo": "Nova obrigação"}
    )


@login_required
def editar_obrigacao(request, pk):
    obrigacao = get_object_or_404(
        queryset_da_empresa(ObrigacaoTecnica.objects.all(), request.user), pk=pk
    )
    if request.method == "POST":
        form = ObrigacaoTecnicaForm(
            request.POST, request.FILES, instance=obrigacao, user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Obrigação atualizada.")
            return redirect("regulatorio_lista")
    else:
        form = ObrigacaoTecnicaForm(instance=obrigacao, user=request.user)
    return render(
        request, "regulatorio/form.html", {"form": form, "titulo": "Editar obrigação"}
    )


@require_POST
@login_required
def baixar_obrigacao(request, pk):
    obrigacao = get_object_or_404(
        queryset_da_empresa(ObrigacaoTecnica.objects.all(), request.user), pk=pk
    )
    obrigacao.status = "baixada"
    obrigacao.save(update_fields=["status"])
    messages.success(request, "Obrigação baixada.")
    return redirect("regulatorio_lista")
