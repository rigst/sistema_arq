from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_safe

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from financeiro.models import ContaBancaria

from .forms import EtapaObraForm, MedicaoForm, ObraForm, VisitaTecnicaForm
from .models import EtapaObra, Medicao, Obra, criar_etapas_obra_padrao
from .services import aprovar_medicao


@require_safe
@login_required
def lista_obras(request):
    obras = queryset_da_empresa(
        Obra.objects.select_related("projeto", "projeto__cliente").prefetch_related("etapas"),
        request.user,
    )
    return render(request, "obras/lista.html", {"obras": obras})


@login_required
def nova_obra(request):
    projeto = projeto_do_pedido(request)
    if request.method == "POST":
        form = ObraForm(request.POST, user=request.user, projeto=projeto)
        if form.is_valid():
            obra = form.save(commit=False)
            obra.empresa = obter_grupo_empresa_ou_erro(request.user)
            obra.criado_por = request.user
            obra.save()
            criar_etapas_obra_padrao(obra)
            messages.success(request, "Execução aberta com etapas construtivas padrão.")
            return redirect("obra_detalhe", pk=obra.pk)
    else:
        form = ObraForm(user=request.user, projeto=projeto)
    return render(
        request, "obras/form.html", {"form": form, "titulo": "Abrir execução", "projeto": projeto}
    )


@login_required
def editar_obra(request, pk):
    obra = get_object_or_404(queryset_da_empresa(Obra.objects.all(), request.user), pk=pk)
    if request.method == "POST":
        form = ObraForm(request.POST, instance=obra, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Obra atualizada.")
            return redirect("obra_detalhe", pk=obra.pk)
    else:
        form = ObraForm(instance=obra, user=request.user)
    return render(request, "obras/form.html", {"form": form, "titulo": "Editar execução"})


@require_safe
@login_required
def detalhe_obra(request, pk):
    obra = get_object_or_404(
        queryset_da_empresa(
            Obra.objects.select_related("projeto", "projeto__cliente").prefetch_related(
                "etapas__medicoes", "visitas__responsavel", "visitas__etapa"
            ),
            request.user,
        ),
        pk=pk,
    )
    medicoes = (
        Medicao.objects.filter(etapa__obra=obra).select_related("etapa").order_by("-data", "-id")
    )
    return render(
        request,
        "obras/detalhe.html",
        {
            "obra": obra,
            "etapas": obra.etapas.all(),
            "visitas": obra.visitas.all()[:20],
            "medicoes": medicoes,
            "form_etapa": EtapaObraForm(),
            "form_visita": VisitaTecnicaForm(obra=obra),
            "form_medicao": MedicaoForm(obra=obra),
            "tem_conta": queryset_da_empresa(ContaBancaria.objects.all(), request.user).exists(),
        },
    )


@require_POST
@login_required
def adicionar_etapa(request, pk):
    obra = get_object_or_404(queryset_da_empresa(Obra.objects.all(), request.user), pk=pk)
    form = EtapaObraForm(request.POST)
    if form.is_valid():
        etapa = form.save(commit=False)
        etapa.obra = obra
        etapa.empresa = obra.empresa
        etapa.save()
        messages.success(request, "Etapa adicionada.")
    else:
        messages.error(request, "Verifique os dados da etapa.")
    return redirect("obra_detalhe", pk=obra.pk)


@require_POST
@login_required
def atualizar_avanco(request, pk):
    etapa = get_object_or_404(queryset_da_empresa(EtapaObra.objects.all(), request.user), pk=pk)
    try:
        etapa.percentual_previsto = _clamp(
            request.POST.get("percentual_previsto", etapa.percentual_previsto)
        )
        etapa.percentual_real = _clamp(request.POST.get("percentual_real", etapa.percentual_real))
        etapa.save(update_fields=["percentual_previsto", "percentual_real"])
        messages.success(request, f"Avanço de “{etapa.nome}” atualizado.")
    # InvalidOperation é o que Decimal("abc") levanta, e ela não é ValueError —
    # herda de ArithmeticError. Sem ela na lista, campo preenchido com texto
    # devolvia 500 em vez da mensagem de erro.
    except (TypeError, ValueError, InvalidOperation):
        messages.error(request, "Percentuais inválidos.")
    return redirect("obra_detalhe", pk=etapa.obra_id)


def _clamp(valor):
    v = Decimal(str(valor))
    return max(Decimal("0"), min(Decimal("100"), v))


@require_POST
@login_required
def registrar_visita(request, pk):
    obra = get_object_or_404(queryset_da_empresa(Obra.objects.all(), request.user), pk=pk)
    form = VisitaTecnicaForm(request.POST, obra=obra)
    if form.is_valid():
        visita = form.save(commit=False)
        visita.obra = obra
        visita.empresa = obra.empresa
        visita.responsavel = request.user
        visita.criado_por = request.user
        visita.save()
        messages.success(request, "Visita técnica registrada.")
    else:
        messages.error(request, "Descreva ao menos o que foi verificado.")
    return redirect("obra_detalhe", pk=obra.pk)


@require_POST
@login_required
def registrar_medicao(request, pk):
    obra = get_object_or_404(queryset_da_empresa(Obra.objects.all(), request.user), pk=pk)
    form = MedicaoForm(request.POST, obra=obra)
    if form.is_valid():
        medicao = form.save(commit=False)
        medicao.empresa = obra.empresa
        medicao.save()
        messages.success(request, "Medição registrada. Aprove para liberar no financeiro.")
    else:
        messages.error(request, "Verifique os dados da medição.")
    return redirect("obra_detalhe", pk=obra.pk)


@require_POST
@login_required
def aprovar_medicao_view(request, pk):
    medicao = get_object_or_404(queryset_da_empresa(Medicao.objects.all(), request.user), pk=pk)
    conta = queryset_da_empresa(ContaBancaria.objects.all(), request.user).first()
    if conta is None:
        messages.error(request, "Crie uma conta no Financeiro antes de liberar a medição.")
        return redirect("obra_detalhe", pk=medicao.etapa.obra_id)
    aprovar_medicao(medicao, conta)
    messages.success(request, "Medição aprovada e lançada no contas a receber.")
    return redirect("obra_detalhe", pk=medicao.etapa.obra_id)
