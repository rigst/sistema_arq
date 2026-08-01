from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from financeiro.models import ContaBancaria

from .forms import AlteracaoEscopoForm, ContratoForm, DocumentoForm, GerarParcelasForm
from .models import Contrato, Parcela
from .services import gerar_parcelas, lancar_parcelas_no_financeiro


@login_required
def lista_contratos(request):
    contratos = queryset_da_empresa(
        Contrato.objects.select_related("projeto", "projeto__cliente"), request.user
    )
    return render(request, "contratos/lista.html", {"contratos": contratos})


@login_required
def novo_contrato(request):
    projeto = projeto_do_pedido(request)
    if request.method == "POST":
        form = ContratoForm(request.POST, user=request.user, projeto=projeto)
        if form.is_valid():
            contrato = form.save(commit=False)
            contrato.empresa = obter_grupo_empresa_ou_erro(request.user)
            contrato.criado_por = request.user
            contrato.save()
            messages.success(request, "Contrato criado.")
            return redirect("contrato_detalhe", pk=contrato.pk)
    else:
        form = ContratoForm(user=request.user, projeto=projeto)
    return render(
        request,
        "contratos/form.html",
        {"form": form, "titulo": "Novo contrato", "projeto": projeto},
    )


@login_required
def editar_contrato(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    if request.method == "POST":
        form = ContratoForm(request.POST, instance=contrato, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato atualizado.")
            return redirect("contrato_detalhe", pk=contrato.pk)
    else:
        form = ContratoForm(instance=contrato, user=request.user)
    return render(
        request, "contratos/form.html", {"form": form, "titulo": f"Editar {contrato.titulo}"}
    )


@login_required
def detalhe_contrato(request, pk):
    contrato = get_object_or_404(
        queryset_da_empresa(Contrato.objects.select_related("projeto", "projeto__cliente"), request.user),
        pk=pk,
    )
    return render(
        request,
        "contratos/detalhe.html",
        {
            "contrato": contrato,
            "parcelas": contrato.parcelas.all(),
            "alteracoes": contrato.alteracoes.all(),
            "documentos": contrato.documentos.all(),
            "form_parcelas": GerarParcelasForm(),
            "form_alteracao": AlteracaoEscopoForm(),
            "form_documento": DocumentoForm(),
            "tem_conta": queryset_da_empresa(ContaBancaria.objects.all(), request.user).exists(),
        },
    )


@login_required
def contrato_pdf(request, pk):
    from django.utils import timezone

    from core.pdf import render_pdf

    contrato = get_object_or_404(
        queryset_da_empresa(Contrato.objects.select_related("projeto", "projeto__cliente"), request.user),
        pk=pk,
    )
    return render_pdf(
        "pdf/contrato.html",
        {
            "contrato": contrato,
            "parcelas": contrato.parcelas.all(),
            "alteracoes": contrato.alteracoes.all(),
            "empresa_nome": request.user.nome_empresa,
            "hoje": timezone.now(),
        },
        filename=f"contrato-{contrato.pk}.pdf",
    )


@require_POST
@login_required
def gerar_parcelas_view(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    if contrato.parcelas_lancadas:
        messages.info(request, "As parcelas já foram lançadas no financeiro; refaça criando outro contrato.")
        return redirect("contrato_detalhe", pk=contrato.pk)
    form = GerarParcelasForm(request.POST)
    if form.is_valid():
        gerar_parcelas(
            contrato,
            form.cleaned_data["quantidade"],
            form.cleaned_data["primeira_data"],
            form.cleaned_data["intervalo_dias"],
        )
        messages.success(request, "Parcelas geradas.")
    else:
        messages.error(request, "Verifique os dados das parcelas.")
    return redirect("contrato_detalhe", pk=contrato.pk)


@require_POST
@login_required
def lancar_financeiro(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    conta = queryset_da_empresa(ContaBancaria.objects.all(), request.user).first()
    if conta is None:
        messages.error(request, "Crie uma conta no Financeiro antes de lançar as parcelas.")
        return redirect("contrato_detalhe", pk=contrato.pk)
    if not contrato.parcelas.exists():
        messages.error(request, "Gere as parcelas primeiro.")
        return redirect("contrato_detalhe", pk=contrato.pk)
    criados = lancar_parcelas_no_financeiro(contrato, conta)
    if contrato.status == "rascunho":
        contrato.status = "ativo"
        contrato.save(update_fields=["status"])
    messages.success(request, f"{criados} parcela(s) lançada(s) no contas a receber.")
    return redirect("contrato_detalhe", pk=contrato.pk)


@require_POST
@login_required
def registrar_alteracao(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    form = AlteracaoEscopoForm(request.POST)
    if form.is_valid():
        alteracao = form.save(commit=False)
        alteracao.contrato = contrato
        alteracao.empresa = contrato.empresa
        alteracao.registrado_por = request.user
        alteracao.save()
        messages.success(request, "Alteração de escopo registrada.")
    return redirect("contrato_detalhe", pk=contrato.pk)


@require_POST
@login_required
def enviar_documento(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    form = DocumentoForm(request.POST, request.FILES)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.contrato = contrato
        doc.projeto = contrato.projeto
        doc.empresa = contrato.empresa
        doc.save()
        messages.success(request, "Documento anexado.")
    else:
        messages.error(request, "Selecione um arquivo e um título.")
    return redirect("contrato_detalhe", pk=contrato.pk)


@require_POST
@login_required
def alternar_parcela(request, pk):
    parcela = get_object_or_404(queryset_da_empresa(Parcela.objects.all(), request.user), pk=pk)
    parcela.paga = not parcela.paga
    parcela.save(update_fields=["paga"])
    # Reflete no lançamento do financeiro.
    if parcela.lancamento_id:
        parcela.lancamento.status = "realizado" if parcela.paga else "previsto"
        parcela.lancamento.save(update_fields=["status"])
    return redirect("contrato_detalhe", pk=parcela.contrato_id)


# =====================================================================
# Modelos de contrato — minutas salvas, geração e apoio de IA
# =====================================================================

from core.ia import IAIndisponivel, disponivel as ia_disponivel, redigir_contrato  # noqa: E402

from .forms import ModeloContratoForm  # noqa: E402
from .models import ModeloContrato  # noqa: E402
from .modelos_padrao import MODELOS_PADRAO  # noqa: E402


def _meus_modelos(user):
    return queryset_da_empresa(ModeloContrato.objects.all(), user)


def _contexto_do_contrato(contrato):
    """Os dados do projeto que preenchem os marcadores da minuta."""
    from django.utils import timezone

    projeto = contrato.projeto
    cliente = projeto.cliente
    obra = getattr(projeto, "obra", None)
    return {
        "cliente": cliente.nome,
        "cliente_documento": getattr(cliente, "documento", "") or "",
        "projeto": projeto.nome,
        "tipo_projeto": projeto.get_tipo_display(),
        "escritorio": contrato.empresa.name,
        "valor": f"R$ {contrato.valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "data": timezone.localdate().strftime("%d/%m/%Y"),
        "prazo": projeto.data_prevista.strftime("%d/%m/%Y") if projeto.data_prevista else "",
        "endereco": getattr(obra, "endereco", "") or "",
    }


@login_required
def modelos_lista(request):
    return render(
        request,
        "contratos/modelos.html",
        {
            "modelos": _meus_modelos(request.user),
            "form": ModeloContratoForm(),
            "marcadores": ModeloContrato.MARCADORES.items(),
        },
    )


@require_POST
@login_required
def modelos_semear(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    criados = 0
    for dados in MODELOS_PADRAO:
        if _meus_modelos(request.user).filter(nome=dados["nome"]).exists():
            continue
        ModeloContrato.objects.create(
            empresa=grupo, criado_por=request.user, **dados
        )
        criados += 1
    if criados:
        messages.success(request, f"{criados} modelo(s) prontos adicionados. Revise o texto.")
    else:
        messages.info(request, "Os modelos prontos já estavam cadastrados.")
    return redirect("contratos_modelos")


@login_required
def modelo_editar(request, pk=None):
    modelo = get_object_or_404(_meus_modelos(request.user), pk=pk) if pk else None
    if request.method == "POST":
        form = ModeloContratoForm(request.POST, instance=modelo)
        if form.is_valid():
            salvo = form.save(commit=False)
            if modelo is None:
                salvo.empresa = obter_grupo_empresa_ou_erro(request.user)
                salvo.criado_por = request.user
            salvo.save()
            messages.success(request, "Modelo salvo.")
            return redirect("contratos_modelos")
    else:
        form = ModeloContratoForm(instance=modelo)
    return render(
        request,
        "contratos/modelo_form.html",
        {"form": form, "modelo": modelo, "marcadores": ModeloContrato.MARCADORES.items()},
    )


@require_POST
@login_required
def modelo_remover(request, pk):
    modelo = get_object_or_404(_meus_modelos(request.user), pk=pk)
    modelo.delete()
    messages.success(request, "Modelo removido.")
    return redirect("contratos_modelos")


@login_required
def redigir(request, pk):
    """Tela onde o contrato ganha texto: gera a partir de um modelo, pede uma
    minuta à IA ou escreve à mão. O texto fica sempre editável."""
    contrato = get_object_or_404(
        queryset_da_empresa(Contrato.objects.select_related("projeto__cliente"), request.user),
        pk=pk,
    )

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "gerar":
            modelo = _meus_modelos(request.user).filter(pk=request.POST.get("modelo")).first()
            if modelo is None:
                messages.error(request, "Escolha um modelo.")
            else:
                contrato.corpo = modelo.gerar(_contexto_do_contrato(contrato))
                contrato.save(update_fields=["corpo"])
                messages.success(request, f"Texto gerado a partir de “{modelo.nome}”. Revise.")
        elif acao == "ia":
            try:
                contrato.corpo = redigir_contrato(
                    _contexto_do_contrato(contrato),
                    request.POST.get("instrucoes", ""),
                )
            except IAIndisponivel as erro:
                messages.error(request, str(erro))
            else:
                contrato.save(update_fields=["corpo"])
                messages.success(
                    request, "Minuta redigida. É um rascunho — revise cláusula por cláusula."
                )
        else:
            contrato.corpo = request.POST.get("corpo", "")
            contrato.save(update_fields=["corpo"])
            messages.success(request, "Texto do contrato salvo.")
        return redirect("contrato_redigir", pk=contrato.pk)

    return render(
        request,
        "contratos/redigir.html",
        {
            "contrato": contrato,
            "modelos": _meus_modelos(request.user).filter(ativo=True),
            "ia_disponivel": ia_disponivel(),
        },
    )
