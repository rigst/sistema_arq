from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa

from .forms import DisciplinaForm, EtapaFornecedorForm, PendenciaForm, ProjetoForm
from .models import Disciplina, Etapa, Pendencia, Projeto, criar_etapas_padrao


@login_required
def painel_projetos(request):
    projetos = queryset_da_empresa(
        Projeto.objects.select_related("cliente").prefetch_related("etapas", "pendencias"),
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
        Projeto.objects.select_related("cliente").prefetch_related("etapas", "pendencias"),
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
            criar_etapas_padrao(projeto)
            messages.success(request, "Projeto criado com etapas padrão.")
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
            "etapas": projeto.etapas.all(),
            "pendencias": projeto.pendencias.all(),
            "form_pendencia": PendenciaForm(),
            "margem": calcular_margem_projeto(projeto),
            "horas_percent": round(horas_percent, 1),
            "disciplinas": projeto.disciplinas.select_related("fornecedor"),
            "form_disciplina": DisciplinaForm(user=request.user),
            "roteiro": roteiro,
            "roteiro_proxima": proxima_etapa(roteiro),
            "roteiro_percent": percentual(roteiro),
        },
    )


@require_POST
@login_required
def avancar_etapa(request, pk):
    etapa = get_object_or_404(queryset_da_empresa(Etapa.objects.all(), request.user), pk=pk)
    if etapa.status == "pendente":
        etapa.status = "andamento"
    elif etapa.status == "andamento":
        etapa.status = "concluida"
        etapa.aprovada = True
        etapa.aprovada_em = timezone.now()
    etapa.save()
    etapa.projeto.tocar()
    messages.success(request, f"Etapa “{etapa.nome}” atualizada.")
    return redirect("projeto_detalhe", pk=etapa.projeto.pk)


@require_POST
@login_required
def adicionar_pendencia(request, pk):
    projeto = get_object_or_404(queryset_da_empresa(Projeto.objects.all(), request.user), pk=pk)
    form = PendenciaForm(request.POST)
    if form.is_valid():
        pendencia = form.save(commit=False)
        pendencia.projeto = projeto
        pendencia.empresa = projeto.empresa
        pendencia.responsavel = request.user
        pendencia.save()
        projeto.tocar()
        messages.success(request, "Pendência adicionada.")
    return redirect("projeto_detalhe", pk=projeto.pk)


@require_POST
@login_required
def resolver_pendencia(request, pk):
    pendencia = get_object_or_404(
        queryset_da_empresa(Pendencia.objects.all(), request.user), pk=pk
    )
    pendencia.resolvida = True
    pendencia.save()
    pendencia.projeto.tocar()
    return redirect("projeto_detalhe", pk=pendencia.projeto.pk)


@require_POST
@login_required
def adicionar_disciplina(request, pk):
    projeto = get_object_or_404(queryset_da_empresa(Projeto.objects.all(), request.user), pk=pk)
    form = DisciplinaForm(request.POST, user=request.user)
    if form.is_valid():
        disciplina = form.save(commit=False)
        disciplina.projeto = projeto
        disciplina.empresa = projeto.empresa
        try:
            disciplina.save()
        except IntegrityError:
            messages.error(request, "Essa disciplina já está no projeto.")
        else:
            projeto.tocar()
            messages.success(request, f"Disciplina “{disciplina.get_nome_display()}” adicionada.")
    else:
        messages.error(request, form.errors.as_text())
    return redirect(reverse("projeto_detalhe", kwargs={"pk": projeto.pk}) + "#elaboracao")


@require_POST
@login_required
def avancar_disciplina(request, pk):
    disciplina = get_object_or_404(
        queryset_da_empresa(Disciplina.objects.all(), request.user), pk=pk
    )
    ordem = ["pendente", "andamento", "concluida"]
    atual = ordem.index(disciplina.status)
    disciplina.status = ordem[min(atual + 1, len(ordem) - 1)]
    disciplina.save(update_fields=["status"])
    disciplina.projeto.tocar()
    return redirect(
        reverse("projeto_detalhe", kwargs={"pk": disciplina.projeto.pk}) + "#elaboracao"
    )


@require_POST
@login_required
def remover_disciplina(request, pk):
    disciplina = get_object_or_404(
        queryset_da_empresa(Disciplina.objects.all(), request.user), pk=pk
    )
    projeto_pk = disciplina.projeto_id
    disciplina.delete()
    return redirect(reverse("projeto_detalhe", kwargs={"pk": projeto_pk}) + "#elaboracao")


@require_POST
@login_required
def definir_fornecedor_etapa(request, pk):
    etapa = get_object_or_404(queryset_da_empresa(Etapa.objects.all(), request.user), pk=pk)
    form = EtapaFornecedorForm(request.POST, instance=etapa, user=request.user)
    if form.is_valid():
        form.save()
        etapa.projeto.tocar()
    return redirect(reverse("projeto_detalhe", kwargs={"pk": etapa.projeto.pk}) + "#elaboracao")
