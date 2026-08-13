import mimetypes
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Max, When
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from financeiro.models import ContaBancaria

from .forms import (
    AlteracaoEscopoForm,
    AssinaturaContratoForm,
    ContratoForm,
    DocumentoEdicaoForm,
    DocumentoForm,
    GerarParcelasForm,
    ParcelaForm,
)
from .models import AlteracaoEscopo, Contrato, Documento, Parcela
from .services import (
    contexto_do_contrato,
    garantir_modelos_padrao,
    gerar_parcelas,
    lancar_parcelas_no_financeiro,
)

MSG_PROPOSTA_PENDENTE = "A aprovação da proposta é necessária antes de criar o contrato."


def _fase_contrato_impeditiva(projeto):
    """A fase de contrato do projeto quando ela impede seguir; None se libera.

    Conferida duas vezes em novo_contrato — no pedido e de novo depois do form
    —, porque o projeto escolhido no formulário pode não ser o da query string.
    """
    if projeto is None:
        return None
    fase = projeto.fases.filter(chave="contrato").first()
    return fase if fase is not None and fase.bloqueada else None


def _modelo_mais_especifico(modelos, tipo_projeto):
    """O do tipo do projeto; na falta, o marcado como padrão; na falta, qualquer um."""
    return (
        modelos.filter(tipo_projeto=tipo_projeto).first()
        or modelos.filter(tipo_projeto="", padrao=True).first()
        or modelos.first()
    )


def _preencher_corpo_padrao(contrato, usuario):
    """Escreve o corpo do contrato a partir do modelo mais específico que
    existir. Contrato que já veio com texto é deixado como está."""
    if contrato.corpo.strip():
        return
    modelos = garantir_modelos_padrao(contrato.empresa, usuario)
    modelo = _modelo_mais_especifico(modelos, contrato.projeto.tipo)
    if modelo is not None:
        contrato.corpo = modelo.gerar(contexto_do_contrato(contrato))
        contrato.save(update_fields=["corpo"])


@login_required
def novo_contrato(request):
    projeto = projeto_do_pedido(request)
    impeditiva = _fase_contrato_impeditiva(projeto)
    if impeditiva is not None:
        messages.error(request, MSG_PROPOSTA_PENDENTE)
        return redirect("fase_detalhe", pk=impeditiva.pk)

    if request.method == "POST":
        form = ContratoForm(request.POST, user=request.user, projeto=projeto)
        if form.is_valid():
            contrato = form.save(commit=False)
            impeditiva = _fase_contrato_impeditiva(contrato.projeto)
            if impeditiva is not None:
                messages.error(request, MSG_PROPOSTA_PENDENTE)
                return redirect("fase_detalhe", pk=impeditiva.pk)
            contrato.empresa = obter_grupo_empresa_ou_erro(request.user)
            contrato.criado_por = request.user
            contrato.save()
            _preencher_corpo_padrao(contrato, request.user)
            messages.success(request, "Contrato criado.")
            return redirect("contrato_detalhe", pk=contrato.pk)
    else:
        form = ContratoForm(user=request.user, projeto=projeto)
    return render(
        request,
        "contratos/form.html",
        {"form": form, "titulo": "Novo contrato", "projeto": projeto},
    )


def _proposta_de_origem(contrato):
    """A proposta que originou o contrato, quando veio de uma."""
    if contrato.origem_tipo != "proposta" or not contrato.origem_id:
        return None
    from propostas.models import Proposta

    return Proposta.objects.filter(pk=contrato.origem_id, empresa=contrato.empresa).first()


def _aplicar_modelo(request, contrato, modelos):
    """Regrava a minuta a partir do modelo escolhido e volta para a âncora."""
    modelo = get_object_or_404(modelos, pk=request.POST.get("modelo"))
    contrato.corpo = modelo.gerar(contexto_do_contrato(contrato))
    contrato.save(update_fields=["corpo"])
    messages.success(request, f"Modelo “{modelo.nome}” aplicado à minuta.")
    return redirect(f"/contratos/{contrato.pk}/#minuta")


@login_required
def detalhe_contrato(request, pk):
    contrato = get_object_or_404(
        queryset_da_empresa(
            Contrato.objects.select_related("projeto", "projeto__cliente"), request.user
        ),
        pk=pk,
    )
    modelos = garantir_modelos_padrao(contrato.empresa, request.user)
    modelo_padrao = _modelo_mais_especifico(modelos, contrato.projeto.tipo)
    modelos = modelos.order_by(
        Case(
            When(tipo_projeto=contrato.projeto.tipo, then=0),
            When(tipo_projeto="", then=1),
            default=2,
            output_field=IntegerField(),
        ),
        "nome",
    )
    proposta_origem = _proposta_de_origem(contrato)
    fases_entrega = list(
        contrato.projeto.fases.exclude(chave__in=("briefing", "proposta", "contrato")).order_by(
            "ordem", "id"
        )
    )
    form = None
    if contrato.editavel:
        if request.method == "POST":
            form = ContratoForm(request.POST, instance=contrato, user=request.user)
            if form.is_valid():
                form.save()
                if request.POST.get("acao") == "aplicar_modelo":
                    return _aplicar_modelo(request, contrato, modelos)
                messages.success(request, "Contrato salvo.")
                return redirect("contrato_detalhe", pk=contrato.pk)
        else:
            form = ContratoForm(instance=contrato, user=request.user)
    alteracoes = list(contrato.alteracoes.all()) if contrato.assinado else []
    impacto_alteracoes = sum((a.valor_delta for a in alteracoes), Decimal("0"))
    return render(
        request,
        "contratos/detalhe.html",
        {
            "contrato": contrato,
            "form": form,
            "parcelas": contrato.parcelas.all() if contrato.assinado else [],
            "alteracoes": alteracoes,
            "impacto_alteracoes": impacto_alteracoes,
            "valor_atualizado": contrato.valor_total + impacto_alteracoes,
            "documentos": contrato.documentos.all(),
            "form_parcelas": GerarParcelasForm(),
            "form_parcela": ParcelaForm(),
            "form_alteracao": AlteracaoEscopoForm(),
            "form_documento": DocumentoForm(),
            "form_assinatura": AssinaturaContratoForm(
                initial={"data_assinatura": timezone.localdate()}
            ),
            "tem_conta": queryset_da_empresa(ContaBancaria.objects.all(), request.user).exists(),
            "modelos": modelos,
            "modelo_padrao": modelo_padrao,
            "proposta_origem": proposta_origem,
            "fases_entrega": fases_entrega,
        },
    )


@require_safe
@login_required
def baixar_documento(request, pk):
    documento = get_object_or_404(
        queryset_da_empresa(Documento.objects.select_related("contrato"), request.user), pk=pk
    )
    if not documento.arquivo:
        raise Http404
    tipo, _ = mimetypes.guess_type(documento.arquivo.name)
    resposta = FileResponse(
        documento.arquivo.open("rb"),
        content_type=tipo or "application/octet-stream",
        as_attachment=True,
        filename=documento.nome_arquivo,
    )
    resposta["X-Content-Type-Options"] = "nosniff"
    return resposta


@require_safe
@login_required
def contrato_pdf(request, pk):
    from django.utils import timezone

    from core.pdf import render_pdf

    contrato = get_object_or_404(
        queryset_da_empresa(
            Contrato.objects.select_related("projeto", "projeto__cliente"), request.user
        ),
        pk=pk,
    )
    alteracoes = list(contrato.alteracoes.all()) if contrato.assinado else []
    impacto = sum((a.valor_delta for a in alteracoes), Decimal("0"))
    return render_pdf(
        "pdf/contrato.html",
        {
            "contrato": contrato,
            "parcelas": contrato.parcelas.all() if contrato.assinado else [],
            "alteracoes": alteracoes,
            "valor_atualizado": contrato.valor_total + impacto,
            "empresa_nome": request.user.nome_empresa,
            "hoje": timezone.now(),
        },
        filename=f"contrato-{contrato.pk}.pdf",
        user=request.user,
    )


@require_POST
@login_required
def gerar_parcelas_view(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    if not _exigir_contrato_assinado(request, contrato):
        return redirect("contrato_detalhe", pk=contrato.pk)
    if contrato.parcelas_lancadas:
        messages.info(
            request, "As parcelas já foram lançadas no financeiro; refaça criando outro contrato."
        )
        return _parcelas_ou_redirect(request, contrato)
    form = GerarParcelasForm(request.POST)
    if form.is_valid():
        gerar_parcelas(
            contrato,
            form.cleaned_data["quantidade"],
            form.cleaned_data["primeira_data"],
        )
        messages.success(request, "Parcelas geradas.")
    else:
        messages.error(request, "Verifique os dados das parcelas.")
    return _parcelas_ou_redirect(request, contrato)


def _parcelas_ou_redirect(request, contrato, form_parcela=None):
    if request.headers.get("HX-Request"):
        return render(
            request,
            "contratos/_parcelas.html",
            {
                "contrato": contrato,
                "parcelas": contrato.parcelas.all(),
                "form_parcelas": GerarParcelasForm(),
                "form_parcela": form_parcela or ParcelaForm(),
                "tem_conta": queryset_da_empresa(
                    ContaBancaria.objects.all(), request.user
                ).exists(),
            },
        )
    return redirect("contrato_detalhe", pk=contrato.pk)


@require_POST
@login_required
def adicionar_parcela(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    if not _exigir_contrato_assinado(request, contrato):
        return redirect("contrato_detalhe", pk=contrato.pk)
    form = ParcelaForm(request.POST)
    if form.is_valid():
        parcela = form.save(commit=False)
        parcela.empresa = contrato.empresa
        parcela.contrato = contrato
        parcela.numero = (contrato.parcelas.aggregate(maior=Max("numero"))["maior"] or 0) + 1
        parcela.save()
        _criar_lancamento_se_necessario(parcela)
        messages.success(request, "Parcela adicionada.")
        return _parcelas_ou_redirect(request, contrato)
    messages.error(request, "Confira descrição, valor e vencimento da parcela.")
    return _parcelas_ou_redirect(request, contrato, form)


@login_required
def editar_parcela(request, pk):
    parcela = get_object_or_404(
        queryset_da_empresa(Parcela.objects.select_related("contrato"), request.user), pk=pk
    )
    if not _exigir_contrato_assinado(request, parcela.contrato):
        return redirect("contrato_detalhe", pk=parcela.contrato_id)
    if request.method == "POST":
        form = ParcelaForm(request.POST, instance=parcela)
        if form.is_valid():
            form.save()
            _sincronizar_lancamento(parcela)
            messages.success(request, "Parcela atualizada.")
            return _parcelas_ou_redirect(request, parcela.contrato)
        return render(
            request,
            TEMPLATE_PARCELA_LINHA,
            {"contrato": parcela.contrato, "parcela": parcela, "form_edicao": form},
        )
    return render(
        request,
        TEMPLATE_PARCELA_LINHA,
        {
            "contrato": parcela.contrato,
            "parcela": parcela,
            "form_edicao": ParcelaForm(instance=parcela),
        },
    )


@require_safe
@login_required
def linha_parcela(request, pk):
    parcela = get_object_or_404(
        queryset_da_empresa(Parcela.objects.select_related("contrato"), request.user), pk=pk
    )
    return render(
        request, TEMPLATE_PARCELA_LINHA, {"contrato": parcela.contrato, "parcela": parcela}
    )


@require_POST
@login_required
def remover_parcela(request, pk):
    parcela = get_object_or_404(
        queryset_da_empresa(Parcela.objects.select_related("contrato", "lancamento"), request.user),
        pk=pk,
    )
    contrato = parcela.contrato
    if not _exigir_contrato_assinado(request, contrato):
        return redirect("contrato_detalhe", pk=contrato.pk)
    if parcela.lancamento_id:
        parcela.lancamento.delete()
    parcela.delete()
    messages.success(request, "Parcela excluída.")
    return _parcelas_ou_redirect(request, contrato)


def _sincronizar_lancamento(parcela):
    if parcela.lancamento_id:
        parcela.lancamento.descricao = (
            parcela.descricao or f"{parcela.contrato.titulo} — parcela {parcela.numero}"
        )
        parcela.lancamento.valor = parcela.valor
        parcela.lancamento.data = parcela.vencimento
        parcela.lancamento.save(update_fields=["descricao", "valor", "data"])


def _criar_lancamento_se_necessario(parcela):
    contrato = parcela.contrato
    if not contrato.parcelas_lancadas:
        return
    conta = (
        contrato.parcelas.exclude(lancamento__isnull=True)
        .select_related("lancamento__conta")
        .values_list("lancamento__conta_id", flat=True)
        .first()
    )
    if conta is None:
        return
    from financeiro.models import Lancamento

    lancamento = Lancamento.objects.create(
        empresa=contrato.empresa,
        conta_id=conta,
        tipo="entrada",
        projeto=contrato.projeto,
        descricao=parcela.descricao or f"{contrato.titulo} — parcela {parcela.numero}",
        valor=parcela.valor,
        data=parcela.vencimento,
        status="previsto",
        origem_tipo="parcela",
        origem_id=parcela.pk,
    )
    parcela.lancamento = lancamento
    parcela.save(update_fields=["lancamento"])


@require_POST
@login_required
def lancar_financeiro(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    if not _exigir_contrato_assinado(request, contrato):
        return redirect("contrato_detalhe", pk=contrato.pk)
    if contrato.status not in {"aprovado", "ativo"}:
        messages.info(request, "Aguarde a aprovação do cliente antes de lançar no financeiro.")
        return redirect("contrato_detalhe", pk=contrato.pk)
    conta = queryset_da_empresa(ContaBancaria.objects.all(), request.user).first()
    if conta is None:
        messages.error(request, "Crie uma conta no Financeiro antes de lançar as parcelas.")
        return redirect("contrato_detalhe", pk=contrato.pk)
    if not contrato.parcelas.exists():
        messages.error(request, "Gere as parcelas primeiro.")
        return redirect("contrato_detalhe", pk=contrato.pk)
    criados = lancar_parcelas_no_financeiro(contrato, conta)
    if contrato.status == "aprovado":
        contrato.status = "ativo"
        contrato.save(update_fields=["status"])
    messages.success(request, f"{criados} parcela(s) lançada(s) no contas a receber.")
    return redirect("contrato_detalhe", pk=contrato.pk)


@require_POST
@login_required
def registrar_alteracao(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    if not _exigir_contrato_assinado(request, contrato):
        return redirect("contrato_detalhe", pk=contrato.pk)
    form = AlteracaoEscopoForm(request.POST)
    formulario_valido = form.is_valid()
    if formulario_valido:
        alteracao = form.save(commit=False)
        alteracao.contrato = contrato
        alteracao.empresa = contrato.empresa
        alteracao.registrado_por = request.user
        alteracao.save()
        if alteracao.valor_delta:
            messages.success(request, "Alteração contratual registrada com impacto financeiro.")
        else:
            messages.success(request, "Alteração contratual registrada sem impacto financeiro.")
    else:
        messages.error(request, "Confira o tipo, a descrição e o impacto financeiro.")
    return _alteracoes_ou_redirect(request, contrato, None if formulario_valido else form)


def _alteracoes_ou_redirect(request, contrato, form=None):
    if request.headers.get("HX-Request"):
        alteracoes = list(contrato.alteracoes.all())
        impacto = sum((a.valor_delta for a in alteracoes), Decimal("0"))
        return render(
            request,
            "contratos/_alteracoes.html",
            {
                "contrato": contrato,
                "alteracoes": alteracoes,
                "impacto_alteracoes": impacto,
                "valor_atualizado": contrato.valor_total + impacto,
                "form_alteracao": form or AlteracaoEscopoForm(),
            },
        )
    return redirect("contrato_detalhe", pk=contrato.pk)


@login_required
def editar_alteracao(request, pk):
    alteracao = get_object_or_404(
        queryset_da_empresa(AlteracaoEscopo.objects.select_related("contrato"), request.user), pk=pk
    )
    if not _exigir_contrato_assinado(request, alteracao.contrato):
        return redirect("contrato_detalhe", pk=alteracao.contrato_id)
    if request.method == "POST":
        form = AlteracaoEscopoForm(request.POST, instance=alteracao)
        if form.is_valid():
            form.save()
            messages.success(request, "Alteração contratual atualizada.")
            return _alteracoes_ou_redirect(request, alteracao.contrato)
    else:
        form = AlteracaoEscopoForm(instance=alteracao)
    return render(
        request,
        "contratos/_alteracao_linha.html",
        {"contrato": alteracao.contrato, "alteracao": alteracao, "form_edicao": form},
    )


@require_safe
@login_required
def linha_alteracao(request, pk):
    alteracao = get_object_or_404(
        queryset_da_empresa(AlteracaoEscopo.objects.select_related("contrato"), request.user), pk=pk
    )
    return render(
        request,
        "contratos/_alteracao_linha.html",
        {"contrato": alteracao.contrato, "alteracao": alteracao},
    )


@require_POST
@login_required
def remover_alteracao(request, pk):
    alteracao = get_object_or_404(
        queryset_da_empresa(AlteracaoEscopo.objects.select_related("contrato"), request.user), pk=pk
    )
    contrato = alteracao.contrato
    if not _exigir_contrato_assinado(request, contrato):
        return redirect("contrato_detalhe", pk=contrato.pk)
    alteracao.delete()
    messages.success(request, "Alteração contratual excluída.")
    return _alteracoes_ou_redirect(request, contrato)


@require_POST
@login_required
def enviar_documento(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    form = DocumentoForm(request.POST, request.FILES)
    formulario_valido = form.is_valid()
    if formulario_valido:
        doc = form.save(commit=False)
        doc.contrato = contrato
        doc.projeto = contrato.projeto
        doc.empresa = contrato.empresa
        doc.save()
        messages.success(request, "Documento anexado.")
    else:
        messages.error(request, "Selecione um arquivo e um título.")
    return _documentos_ou_redirect(request, contrato, None if formulario_valido else form)


def _documentos_ou_redirect(request, contrato, form=None):
    if request.headers.get("HX-Request"):
        return render(
            request,
            "contratos/_documentos.html",
            {
                "contrato": contrato,
                "documentos": contrato.documentos.all(),
                "form_documento": form or DocumentoForm(),
            },
        )
    return redirect("contrato_detalhe", pk=contrato.pk)


@login_required
def editar_documento(request, pk):
    documento = get_object_or_404(
        queryset_da_empresa(Documento.objects.select_related("contrato"), request.user), pk=pk
    )
    arquivo_antigo = documento.arquivo.name
    if request.method == "POST":
        form = DocumentoEdicaoForm(request.POST, request.FILES, instance=documento)
        if form.is_valid():
            form.save()
            if request.FILES.get("arquivo") and arquivo_antigo != documento.arquivo.name:
                documento.arquivo.storage.delete(arquivo_antigo)
            messages.success(request, "Documento atualizado.")
            return _documentos_ou_redirect(request, documento.contrato)
    else:
        form = DocumentoEdicaoForm(instance=documento)
    return render(
        request,
        "contratos/_documento_linha.html",
        {"contrato": documento.contrato, "documento": documento, "form_edicao": form},
    )


@require_safe
@login_required
def linha_documento(request, pk):
    documento = get_object_or_404(
        queryset_da_empresa(Documento.objects.select_related("contrato"), request.user), pk=pk
    )
    return render(
        request,
        "contratos/_documento_linha.html",
        {"contrato": documento.contrato, "documento": documento},
    )


@require_POST
@login_required
def remover_documento(request, pk):
    documento = get_object_or_404(
        queryset_da_empresa(Documento.objects.select_related("contrato"), request.user),
        pk=pk,
    )
    contrato_pk = documento.contrato_id
    documento.arquivo.delete(save=False)
    documento.delete()
    messages.success(request, "Documento removido do contrato.")
    contrato = get_object_or_404(
        queryset_da_empresa(Contrato.objects.all(), request.user), pk=contrato_pk
    )
    return _documentos_ou_redirect(request, contrato)


@require_POST
@login_required
def alternar_parcela(request, pk):
    parcela = get_object_or_404(queryset_da_empresa(Parcela.objects.all(), request.user), pk=pk)
    if not _exigir_contrato_assinado(request, parcela.contrato):
        return redirect("contrato_detalhe", pk=parcela.contrato_id)
    parcela.paga = not parcela.paga
    parcela.save(update_fields=["paga"])
    # Reflete no lançamento do financeiro.
    if parcela.lancamento_id:
        parcela.lancamento.status = "realizado" if parcela.paga else "previsto"
        parcela.lancamento.save(update_fields=["status"])
    return _parcelas_ou_redirect(request, parcela.contrato)


@require_POST
@login_required
def enviar_contrato(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    if not contrato.editavel:
        messages.info(request, "Este contrato já foi enviado ao cliente.")
    elif not contrato.pronto_para_envio:
        messages.error(request, "Inclua o texto do contrato e um valor total antes de enviar.")
    else:
        contrato.status = "enviado"
        contrato.save(update_fields=["status"])
        messages.success(
            request, "Contrato enviado ao cliente. A edição foi bloqueada até um retorno."
        )
    return redirect("contrato_detalhe", pk=contrato.pk)


@require_POST
@login_required
def retornar_para_ajustes(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    if contrato.status != "enviado":
        messages.info(request, "Somente contratos enviados podem retornar para alterações.")
    else:
        contrato.status = "ajustes"
        contrato.save(update_fields=["status"])
        messages.success(request, "Contrato retornado para alterações. Revise e envie novamente.")
    return redirect("contrato_detalhe", pk=contrato.pk)


@require_POST
@login_required
def aprovar_contrato(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    if contrato.status != "enviado":
        messages.info(request, "Registre a aprovação somente depois do envio ao cliente.")
    else:
        contrato.status = "ativo" if contrato.assinado else "aprovado"
        contrato.save(update_fields=["status"])
        from fases.models import Fase

        fase = contrato.projeto.fases.filter(chave="contrato").first()
        if fase and fase.status != Fase.APROVADA:
            fase.status = Fase.APROVADA
            fase.respondida_em = timezone.now()
            fase.save(update_fields=["status", "respondida_em"])
            fase._abrir_seguintes(request.user)
            fase.projeto.tocar()
        if contrato.assinado:
            messages.success(
                request,
                "Contrato aprovado e assinatura registrada. Parcelas e alterações estão liberadas.",
            )
        else:
            messages.success(
                request,
                "Contrato aprovado. Registre a assinatura para liberar parcelas e alterações.",
            )
    return redirect("contrato_detalhe", pk=contrato.pk)


def _exigir_contrato_assinado(request, contrato):
    if contrato.assinado:
        return True
    messages.error(
        request,
        "Registre a assinatura do contrato antes de acessar parcelas ou alterações contratuais.",
    )
    return False


@require_POST
@login_required
def registrar_assinatura(request, pk):
    contrato = get_object_or_404(queryset_da_empresa(Contrato.objects.all(), request.user), pk=pk)
    if contrato.status != "aprovado":
        messages.info(
            request, "A assinatura só pode ser registrada depois da aprovação do contrato."
        )
        return redirect("contrato_detalhe", pk=contrato.pk)
    form = AssinaturaContratoForm(request.POST)
    if form.is_valid():
        contrato.data_assinatura = form.cleaned_data["data_assinatura"]
        contrato.status = "ativo"
        contrato.save(update_fields=["data_assinatura", "status"])
        messages.success(
            request, "Assinatura registrada. Parcelas e alterações contratuais estão liberadas."
        )
    else:
        messages.error(request, "Informe uma data de assinatura válida.")
    return redirect("contrato_detalhe", pk=contrato.pk)


# =====================================================================
# Modelos de contrato — minutas salvas, geração e apoio de IA
# =====================================================================


from .forms import ModeloContratoForm  # noqa: E402
from .modelos_padrao import MODELOS_PADRAO  # noqa: E402
from .models import ModeloContrato  # noqa: E402

TEMPLATE_PARCELA_LINHA = "contratos/_parcela_linha.html"


def _meus_modelos(user):
    return queryset_da_empresa(ModeloContrato.objects.all(), user)


@require_safe
@login_required
def modelos_lista(request):
    return redirect("modelos")


@require_POST
@login_required
def modelos_semear(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    criados = 0
    for dados in MODELOS_PADRAO:
        if _meus_modelos(request.user).filter(nome=dados["nome"]).exists():
            continue
        ModeloContrato.objects.create(empresa=grupo, criado_por=request.user, **dados)
        criados += 1
    if criados:
        messages.success(request, f"{criados} modelo(s) prontos adicionados. Revise o texto.")
    else:
        messages.info(request, "Os modelos prontos já estavam cadastrados.")
    return redirect("modelos")


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
                salvo.ativo = True
            salvo.save()
            messages.success(request, "Modelo salvo.")
            return redirect("modelos")
    else:
        initial = None
        if modelo is None:
            initial = {
                "ativo": True,
                "corpo": (
                    "CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE ARQUITETURA\n\n"
                    "CONTRATANTE: {{cliente}}, CPF/CNPJ nº {{cliente_documento}}.\n"
                    "CONTRATADA: {{escritorio}}.\n\n"
                    "CLÁUSULA 1 — OBJETO E ESCOPO\n{{escopo}}\n\n"
                    "CLÁUSULA 2 — PRAZOS E APROVAÇÕES\n{{cronograma}}\n\n"
                    "CLÁUSULA 3 — HONORÁRIOS E PAGAMENTO\n{{valor}}.\n\n"
                    "CLÁUSULA 4 — RESPONSABILIDADES E RRT\n[PREENCHER]\n\n"
                    "CLÁUSULA 5 — ALTERAÇÕES DE ESCOPO\n[PREENCHER]\n\n"
                    "CLÁUSULA 6 — DIREITOS AUTORAIS E USO\n[PREENCHER]\n\n"
                    "CLÁUSULA 7 — RESCISÃO E FORO\n[PREENCHER]\n\n"
                    "{{data}}"
                ),
            }
        form = ModeloContratoForm(instance=modelo, initial=initial)
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
    return redirect("modelos")
