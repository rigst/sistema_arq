from django.contrib import messages
from django.db.models import Count, F, Q, Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.tenancy import queryset_da_empresa
from fases.catalogo import COMPLEMENTARES_NOMEADOS
from fases.forms import LembreteForm
from fases.models import Fase, montar_fases
from fases.services import garantir_tarefas_do_projeto
from tarefas.models import Tarefa

from .forms import PlanejamentoProjetoForm, ProjetoForm
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


@require_POST
@login_required
def remover_projeto(request, pk):
    projeto = get_object_or_404(queryset_da_empresa(Projeto.objects.all(), request.user), pk=pk)
    nome = projeto.nome
    projeto.delete()
    messages.success(request, f"Projeto “{nome}” excluído.")
    return redirect("projetos_painel")


@require_POST
@login_required
def atualizar_planejamento(request, pk):
    projeto = get_object_or_404(queryset_da_empresa(Projeto.objects.all(), request.user), pk=pk)
    form = PlanejamentoProjetoForm(request.POST, instance=projeto)
    if form.is_valid():
        form.save()
        projeto.tocar()
        messages.success(request, "Planejamento de horas e entregas atualizado.")
    else:
        messages.error(request, "Confira as horas e as datas de entrega.")
    return redirect("projeto_detalhe", pk=projeto.pk)


def _contexto_tarefas(projeto):
    tarefas = projeto.tarefas.filter(fase__isnull=False).exclude(
        fase__status=Fase.NAO_INICIADA
    )
    totais = tarefas.aggregate(
        total=Count("id"),
        concluidas=Count("id", filter=Q(status="concluida")),
        horas=Sum("horas_previstas"),
    )
    total = totais["total"] or 0
    concluidas = totais["concluidas"] or 0
    return {
        "tarefas_total": total,
        "tarefas_concluidas": concluidas,
        "tarefas_pendentes": total - concluidas,
        "tarefas_horas": totais["horas"] or 0,
        "tarefas_percent": round(concluidas / total * 100, 1) if total else 0,
        "proximas_tarefas": tarefas.exclude(status="concluida")
        .select_related("fase")
        .order_by(F("prazo").asc(nulls_last=True), "fase__ordem", "ordem", "id")[:5],
        "form_planejamento": PlanejamentoProjetoForm(instance=projeto),
    }


def contexto_arquivos_principais(projeto, contrato=None):
    from briefing.models import Briefing
    from contratos.models import Documento
    from propostas.models import Proposta

    contrato = contrato or projeto.contratos.order_by("-criado_em").first()
    briefing = Briefing.objects.filter(projeto=projeto).first()
    proposta = Proposta.objects.filter(projeto_gerado=projeto).first()
    documentos = list(
        Documento.objects.filter(projeto=projeto).select_related("contrato")
    )
    favoritos = list(
        projeto.arquivos.filter(favorito=True, fase__isnull=False).select_related(
            "fase", "criado_por"
        )
    )
    return {
        "projeto": projeto,
        "briefing_principal": briefing,
        "proposta_principal": proposta,
        "contrato_principal": contrato,
        "documentos_contrato": documentos,
        "arquivos_favoritos": favoritos,
        "tem_arquivos_principais": bool(
            briefing or proposta or (contrato and contrato.corpo.strip()) or documentos or favoritos
        ),
    }


@login_required
def detalhe_projeto(request, pk):
    from jornada.roteiro import montar_roteiro, percentual, proxima_etapa

    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.select_related("cliente"), request.user), pk=pk
    )
    # A ficha é a fonte visual do fluxo: recompõe fases principais que possam
    # faltar em projetos antigos e normaliza a ordem antes de apresentá-las.
    montar_fases(projeto)
    contrato = projeto.contratos.order_by("-criado_em").first()
    garantir_tarefas_do_projeto(projeto, request.user)
    # O roteiro mora aqui, e não numa página só dele: ter duas telas centrais
    # por projeto era o que fazia ninguém saber em qual delas olhar.
    roteiro = montar_roteiro(projeto)
    fases = projeto.fases.select_related("fornecedor").annotate(
        horas_tarefas=Sum("tarefas__horas_previstas")
    ).order_by("ordem", "id")
    fases_principais = [fase for fase in fases if not fase.complementar]
    fases_complementares = [fase for fase in fases if fase.complementar]
    executivo = next((fase for fase in fases_principais if fase.chave == "executivo"), None)
    contexto = {
        "projeto": projeto,
        "valor_contrato": contrato.valor_total if contrato else projeto.valor_contratado,
        "lembretes": projeto.lembretes.filter(fase__isnull=True).select_related("autor"),
        "form_lembrete": LembreteForm(),
        "acao_lembrete": reverse("projeto_lembrete", kwargs={"projeto_pk": projeto.pk}),
        "complementares_marcados": set(
            projeto.fases.values_list("chave", flat=True)
        ),
        "fases": fases,
        "fases_principais": fases_principais,
        "fases_complementares": fases_complementares,
        "complementares_liberados": bool(executivo and executivo.status == Fase.APROVADA),
        "complementares_todos": COMPLEMENTARES_NOMEADOS,
        "complementares_extras": projeto.fases.filter(chave="comp_outro"),
        "roteiro": roteiro,
        "roteiro_proxima": proxima_etapa(roteiro),
        "roteiro_percent": percentual(roteiro),
    }
    contexto.update(_contexto_tarefas(projeto))
    contexto.update(contexto_arquivos_principais(projeto, contrato))
    return render(
        request,
        "projetos/detalhe.html",
        contexto,
    )


@require_POST
@login_required
def alternar_tarefa(request, pk):
    tarefa = get_object_or_404(
        queryset_da_empresa(
            Tarefa.objects.select_related("projeto", "fase"), request.user
        ),
        pk=pk,
        projeto__isnull=False,
        fase__isnull=False,
    )
    if tarefa.fase.bloqueada:
        messages.error(request, "Esta tarefa pertence a uma fase ainda bloqueada.")
        return redirect(reverse("projeto_detalhe", kwargs={"pk": tarefa.projeto_id}) + "#tarefas")
    tarefa.status = "aberta" if tarefa.status == "concluida" else "concluida"
    tarefa.save(update_fields=["status"])
    tarefa.projeto.tocar()
    if request.headers.get("HX-Request"):
        contexto = {
            "projeto": tarefa.projeto,
            "tarefa_feedback": tarefa.titulo,
            "tarefa_foi_concluida": tarefa.status == "concluida",
        }
        contexto.update(_contexto_tarefas(tarefa.projeto))
        return render(request, "projetos/_proximas_tarefas.html", contexto)
    return redirect(reverse("projeto_detalhe", kwargs={"pk": tarefa.projeto_id}) + "#tarefas")
