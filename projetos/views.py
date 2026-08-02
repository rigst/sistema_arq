from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from fases.catalogo import COMPLEMENTARES_NOMEADOS
from fases.forms import LembreteForm
from fases.models import montar_fases

from .forms import ProjetoForm
from .models import Projeto


@login_required
def painel_projetos(request):
    projetos = queryset_da_empresa(
        Projeto.objects.select_related("cliente").prefetch_related("fases", "lembretes"),
        request.user,
    )
    status = request.GET.get("status", "")
    if status:
        projetos = projetos.filter(status=status)
    return render(
        request,
        "projetos/painel.html",
        {"projetos": projetos, "status_ativo": status, "status_choices": Projeto.STATUS_CHOICES},
    )


@login_required
def kanban_projetos(request):
    projetos = queryset_da_empresa(
        Projeto.objects.select_related("cliente").prefetch_related("fases", "lembretes"),
        request.user,
    )
    colunas = [
        (valor, rotulo, [p for p in projetos if p.status == valor])
        for valor, rotulo in Projeto.STATUS_CHOICES
    ]
    return render(request, "projetos/kanban.html", {"colunas": colunas})


@require_POST
@login_required
def mover_status(request, pk):
    projeto = get_object_or_404(queryset_da_empresa(Projeto.objects.all(), request.user), pk=pk)
    novo = request.POST.get("status", "")
    if novo in dict(Projeto.STATUS_CHOICES):
        projeto.status = novo
        projeto.ultima_atualizacao = timezone.now()
        projeto.save(update_fields=["status", "ultima_atualizacao"])
    if request.headers.get("HX-Request"):
        return render(request, "projetos/_card_kanban.html", {"p": projeto})
    return redirect("projetos_kanban")


@login_required
def novo_projeto(request):
    if request.method == "POST":
        form = ProjetoForm(request.POST, user=request.user)
        if form.is_valid():
            projeto = form.save(commit=False)
            projeto.empresa = obter_grupo_empresa_ou_erro(request.user)
            projeto.criado_por = request.user
            projeto.save()
            form.save_m2m()
            montar_fases(projeto)
            messages.success(request, "Projeto criado. O fluxo começa pelo briefing.")
            return redirect("projeto_detalhe", pk=projeto.pk)
    else:
        form = ProjetoForm(user=request.user)
    return render(request, "projetos/form.html", {"form": form, "titulo": "Novo projeto"})


@login_required
def editar_projeto(request, pk):
    projeto = get_object_or_404(queryset_da_empresa(Projeto.objects.all(), request.user), pk=pk)
    if request.method == "POST":
        form = ProjetoForm(request.POST, instance=projeto, user=request.user)
        if form.is_valid():
            form.save()
            projeto.tocar()
            messages.success(request, "Projeto atualizado.")
            return redirect("projeto_detalhe", pk=projeto.pk)
    else:
        form = ProjetoForm(instance=projeto, user=request.user)
    return render(
        request, "projetos/form.html", {"form": form, "titulo": f"Editar {projeto.nome}"}
    )


@login_required
def detalhe_projeto(request, pk):
    from financeiro.services import calcular_margem_projeto
    from jornada.roteiro import montar_roteiro, percentual, proxima_etapa

    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.select_related("cliente"), request.user), pk=pk
    )
    trabalhadas = projeto.horas_trabalhadas
    estimadas = projeto.horas_estimadas or 0
    horas_percent = min(float(trabalhadas) / float(estimadas) * 100, 100) if estimadas else 0
    # O roteiro mora aqui, e não numa página só dele: ter duas telas centrais
    # por projeto era o que fazia ninguém saber em qual delas olhar.
    roteiro = montar_roteiro(projeto)
    return render(
        request,
        "projetos/detalhe.html",
        {
            "projeto": projeto,
            "lembretes_fixados": projeto.lembretes.filter(
                fixado=True, fase__isnull=True
            ).select_related("autor"),
            "lembretes_arquivados": list(
                projeto.lembretes.filter(fixado=False, fase__isnull=True).select_related("autor")
            ),
            "form_lembrete": LembreteForm(),
            "acao_lembrete": reverse("projeto_lembrete", kwargs={"projeto_pk": projeto.pk}),
            "complementares_marcados": set(
                projeto.fases.values_list("chave", flat=True)
            ),
            "margem": calcular_margem_projeto(projeto),
            "horas_percent": round(horas_percent, 1),
            "fases": projeto.fases.select_related("fornecedor"),
            "complementares_todos": COMPLEMENTARES_NOMEADOS,
            "roteiro": roteiro,
            "roteiro_proxima": proxima_etapa(roteiro),
            "roteiro_percent": percentual(roteiro),
        },
    )
