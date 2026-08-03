from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from decimal import Decimal, InvalidOperation

from core.tenancy import queryset_da_empresa
from precificacao.models import FatorPrecificacao
from precificacao.services import aplicar_fatores, hora_tecnica_base, precificar_etapa
from projetos.models import Projeto

from . import itens_prontos
from .forms import ItemPropostaForm, PropostaForm
from .models import ItemProposta, Proposta


def _reprecificar_itens(proposta):
    """Recalcula o valor de todos os itens com a hora técnica atual da proposta."""
    for item in proposta.itens.all():
        calc = precificar_etapa(
            proposta.empresa, item.horas_estimadas, hora_tecnica=proposta.hora_tecnica_aplicada
        )
        item.valor = calc["total"]
        item.save(update_fields=["valor"])


def _ordenar_itens(proposta):
    """Normaliza posições sem desfazer a ordem escolhida pelo usuário."""
    itens = list(proposta.itens.order_by("ordem", "pk"))
    for ordem, item in enumerate(itens):
        if item.ordem != ordem:
            item.ordem = ordem
            item.save(update_fields=["ordem"])


@login_required
def detalhe_proposta(request, pk):
    proposta = get_object_or_404(
        queryset_da_empresa(
            Proposta.objects.select_related("cliente", "projeto_gerado"), request.user
        ),
        pk=pk,
    )
    fases_entrega = _fases_de_entrega(proposta)
    fatores = queryset_da_empresa(FatorPrecificacao.objects.filter(ativo=True), request.user)
    selecionados = set(proposta.fatores.values_list("pk", flat=True))
    form_termos = None
    if proposta.editavel:
        if request.method == "POST":
            form_termos = PropostaForm(request.POST, instance=proposta, user=request.user)
            prazos_validos, prazos = _prazos_do_post(request, fases_entrega)
            if form_termos.is_valid() and prazos_validos:
                with transaction.atomic():
                    form_termos.save()
                    for fase, prazo in prazos:
                        fase.dias_uteis_proposta = prazo
                        fase.save(update_fields=["dias_uteis_proposta"])
                    if request.POST.get("acao") == "enviar":
                        _enviar_ao_cliente(request, proposta)
                    else:
                        messages.success(request, "Proposta salva.")
                return redirect("proposta_detalhe", pk=proposta.pk)
            if not form_termos.is_valid():
                erros = "; ".join(
                    f"{form_termos.fields[campo].label}: {' '.join(mensagens)}"
                    for campo, mensagens in form_termos.errors.items()
                    if campo in form_termos.fields
                )
                messages.error(
                    request,
                    f"A proposta não foi salva. {erros or 'Confira os campos obrigatórios.'}",
                )
        else:
            form_termos = PropostaForm(instance=proposta, user=request.user)
    return render(
        request,
        "propostas/detalhe.html",
        {
            "proposta": proposta,
            "itens": proposta.itens.all(),
            "form_item": ItemPropostaForm(),
            "prontos": itens_prontos.por_grupo(),
            "base": hora_tecnica_base(proposta.empresa),
            "fatores": fatores,
            "fatores_selecionados": selecionados,
            "form_termos": form_termos,
            "fases_entrega": fases_entrega,
        },
    )


def _fases_de_entrega(proposta):
    if proposta.projeto_gerado_id is None:
        return []
    return list(
        proposta.projeto_gerado.fases.exclude(
            chave__in=("briefing", "proposta", "contrato")
        ).order_by("ordem", "id")
    )


def _prazos_do_post(request, fases):
    prazos = []
    for fase in fases:
        campo = f"dias_fase_{fase.pk}"
        if campo not in request.POST:
            continue
        valor = request.POST.get(campo, "").strip()
        try:
            prazo = int(valor) if valor else None
            if prazo is not None and prazo < 1:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(
                request,
                f"A proposta não foi salva. Informe um número válido de dias úteis para {fase.nome}.",
            )
            return False, []
        prazos.append((fase, prazo))
    return True, prazos


def criar_proposta_do_projeto(projeto, usuario):
    """Cria o rascunho que sucede o briefing, sem uma tela intermediária."""
    existente = getattr(projeto, "proposta_origem", None)
    if existente is not None:
        return existente
    return Proposta.objects.create(
        empresa=projeto.empresa,
        criado_por=usuario,
        cliente=projeto.cliente,
        projeto_gerado=projeto,
        titulo=f"Proposta — {projeto.nome}",
        tipo_projeto=projeto.tipo,
        hora_tecnica_aplicada=hora_tecnica_base(projeto.empresa),
    )


@require_POST
@login_required
def definir_hora_tecnica(request, pk):
    """Usuário escolhe a hora técnica da proposta: valor manual livre e/ou fatores
    de projeto aplicados sobre a hora-base. Reprecifica os itens existentes."""
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    if not proposta.editavel:
        messages.info(request, "Proposta enviada; retorne-a para edição antes de alterar a hora técnica.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    fatores_ids = request.POST.getlist("fatores")
    fatores = list(
        queryset_da_empresa(FatorPrecificacao.objects.filter(ativo=True), request.user).filter(
            pk__in=fatores_ids
        )
    )

    valor_manual = request.POST.get("valor_manual", "").strip()
    if "," in valor_manual:
        valor_manual = valor_manual.replace(".", "").replace(",", ".")
    if valor_manual:
        try:
            hora_aplicada = Decimal(valor_manual)
        except (InvalidOperation, ValueError):
            messages.error(request, "Valor de hora técnica inválido.")
            return redirect("proposta_detalhe", pk=proposta.pk)
        if hora_aplicada <= 0:
            messages.error(request, "A hora técnica deve ser maior que zero.")
            return redirect("proposta_detalhe", pk=proposta.pk)
    else:
        hora_aplicada = aplicar_fatores(hora_tecnica_base(proposta.empresa), fatores)

    with transaction.atomic():
        proposta.fatores.set(fatores)
        proposta.hora_tecnica_aplicada = hora_aplicada
        proposta.save(update_fields=["hora_tecnica_aplicada"])
        _reprecificar_itens(proposta)
    messages.success(
        request, f"Hora técnica desta proposta: R$ {proposta.hora_tecnica_aplicada}."
    )
    return redirect("proposta_detalhe", pk=proposta.pk)


@require_POST
@login_required
def adicionar_prontos(request, pk):
    """Joga na proposta um conjunto de linhas prontas, já precificadas.

    O que trava a proposta não é o cálculo: é a folha em branco às dez da noite.
    """
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    if not proposta.editavel:
        messages.info(request, "Proposta enviada; retorne-a para edição antes de incluir itens.")
        return redirect("proposta_detalhe", pk=proposta.pk)
    escolhidos = set(request.POST.getlist("prontos"))
    if not escolhidos:
        messages.error(request, "Marque ao menos um item.")
        return _itens_ou_redirect(request, proposta)

    ja_tem = {i.descricao for i in proposta.itens.all()}
    ordem = proposta.itens.count()
    criados = 0
    for _, itens in itens_prontos.por_grupo():
        for descricao, horas, inclusoes in itens:
            if descricao not in escolhidos or descricao in ja_tem:
                continue
            calc = precificar_etapa(
                proposta.empresa, horas, hora_tecnica=proposta.hora_tecnica_aplicada
            )
            ItemProposta.objects.create(
                empresa=proposta.empresa, proposta=proposta, descricao=descricao,
                inclusoes=inclusoes, horas_estimadas=horas,
                valor=calc["total"], ordem=ordem + criados,
            )
            criados += 1
    if criados:
        _ordenar_itens(proposta)
        messages.success(request, f"{criados} item(ns) adicionados e precificados. Ajuste as horas.")
    else:
        messages.info(request, "Esses itens já estavam na proposta.")
    return _itens_ou_redirect(request, proposta)


@require_POST
@login_required
def adicionar_item(request, pk):
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    if not proposta.editavel:
        messages.info(request, "Proposta enviada; retorne-a para edição antes de incluir itens.")
        return redirect("proposta_detalhe", pk=proposta.pk)
    form = ItemPropostaForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        calc = precificar_etapa(
            proposta.empresa, item.horas_estimadas, hora_tecnica=proposta.hora_tecnica_aplicada
        )
        item.proposta = proposta
        item.empresa = proposta.empresa
        item.valor = calc["total"]
        item.ordem = proposta.itens.count()
        item.save()
        _ordenar_itens(proposta)
        messages.success(request, "Item precificado e adicionado.")
    else:
        messages.error(request, "O item não foi adicionado. Informe etapa, o que inclui e horas.")
    return _itens_ou_redirect(request, proposta)


@login_required
def editar_item(request, pk):
    """Edição no lugar: a linha vira campos e volta pronta.

    Uma tela só para corrigir "40 h" para "36 h" custa mais do que a correção,
    e obriga a perder de vista o resto da proposta — que é justamente o que se
    está comparando ao mexer numa linha.
    """
    item = get_object_or_404(
        queryset_da_empresa(ItemProposta.objects.select_related("proposta"), request.user), pk=pk
    )
    proposta = item.proposta
    if not proposta.editavel:
        messages.info(request, "Proposta enviada; volte-a para edição antes de mexer nos itens.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    if request.method == "POST":
        form = ItemPropostaForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save(commit=False)
            calc = precificar_etapa(
                proposta.empresa, item.horas_estimadas,
                hora_tecnica=proposta.hora_tecnica_aplicada,
            )
            item.valor = calc["total"]
            item.save()
            _ordenar_itens(proposta)
            messages.success(request, f"“{item.descricao}” atualizado.")
            return _itens_ou_redirect(request, proposta)
        messages.error(request, "O item não foi salvo. Informe etapa, o que inclui e horas.")
        return _itens_ou_redirect(request, proposta)

    # GET: devolve só a linha, em modo de edição.
    return render(
        request,
        "propostas/_item_linha.html",
        {"item": item, "proposta": proposta, "form_edicao": ItemPropostaForm(instance=item)},
    )


@login_required
def linha_item(request, pk):
    """A mesma linha em leitura — é o que o Cancelar da edição traz de volta."""
    item = get_object_or_404(
        queryset_da_empresa(ItemProposta.objects.select_related("proposta"), request.user), pk=pk
    )
    itens = list(item.proposta.itens.order_by("ordem", "pk"))
    indice = next(i for i, atual in enumerate(itens) if atual.pk == item.pk)
    return render(
        request,
        "propostas/_item_linha.html",
        {
            "item": item,
            "proposta": item.proposta,
            "pode_subir": indice > 0,
            "pode_descer": indice < len(itens) - 1,
        },
    )


def _itens_ou_redirect(request, proposta):
    """Troca só o bloco de itens quando quem pediu foi o htmx.

    O total mora no rodapé da tabela: devolver a linha sozinha deixaria o
    número velho na tela, que é pior do que não atualizar nada.
    """
    if request.headers.get("HX-Request"):
        return render(
            request,
            "propostas/_itens.html",
            {
                "proposta": proposta,
                "itens": proposta.itens.all(),
                "form_item": ItemPropostaForm(),
            },
        )
    return redirect("proposta_detalhe", pk=proposta.pk)


@require_POST
@login_required
def remover_item(request, pk):
    item = get_object_or_404(
        queryset_da_empresa(ItemProposta.objects.select_related("proposta"), request.user), pk=pk
    )
    proposta = item.proposta
    if not proposta.editavel:
        messages.info(request, "Proposta enviada; volte-a para edição antes de mexer nos itens.")
        return redirect("proposta_detalhe", pk=proposta.pk)
    item.delete()
    _ordenar_itens(proposta)
    return _itens_ou_redirect(request, proposta)


@require_POST
@login_required
def mover_item(request, pk):
    """Move um serviço uma posição; a ordem também é usada no PDF."""
    item = get_object_or_404(
        queryset_da_empresa(ItemProposta.objects.select_related("proposta"), request.user),
        pk=pk,
    )
    proposta = item.proposta
    if not proposta.editavel:
        messages.info(request, "Proposta enviada; volte-a para edição antes de reordenar os itens.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    direcao = request.POST.get("direcao")
    if direcao not in {"cima", "baixo"}:
        messages.error(request, "Direção inválida para reordenar o serviço.")
        return _itens_ou_redirect(request, proposta)

    with transaction.atomic():
        itens = list(proposta.itens.select_for_update().order_by("ordem", "pk"))
        indice = next(i for i, atual in enumerate(itens) if atual.pk == item.pk)
        destino = indice - 1 if direcao == "cima" else indice + 1
        if 0 <= destino < len(itens):
            itens[indice], itens[destino] = itens[destino], itens[indice]
            for ordem, atual in enumerate(itens):
                atual.ordem = ordem
            ItemProposta.objects.bulk_update(itens, ["ordem"])
    return _itens_ou_redirect(request, proposta)


@require_POST
@login_required
def finalizar_proposta(request, pk):
    """Fecha a proposta e a manda ao cliente. A partir daqui, ela não muda."""
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    _enviar_ao_cliente(request, proposta)
    return redirect("proposta_detalhe", pk=proposta.pk)


def _enviar_ao_cliente(request, proposta):
    """Valida e registra o envio, usado pela tela única e pela rota legada."""
    if not proposta.editavel:
        messages.info(request, "Esta proposta já foi enviada.")
        return False
    if not proposta.itens.exists():
        messages.error(request, "Uma proposta sem itens não tem o que enviar.")
        return False

    proposta.status = "enviada"
    proposta.save(update_fields=["status"])
    messages.success(
        request, f"“{proposta.titulo}” enviada ao cliente por R$ {proposta.valor_total}."
    )
    return True


@require_POST
@login_required
def reabrir_proposta(request, pk):
    """Cliente não aprovou: volta para edição, para refazer e mandar de novo."""
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    if proposta.status == "aprovada":
        messages.info(request, "Proposta aprovada não volta para edição.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    proposta.status = "rascunho"
    proposta.save(update_fields=["status"])
    messages.success(request, "Proposta reaberta. Ajuste o que for preciso e envie de novo.")
    return redirect("proposta_detalhe", pk=proposta.pk)


@login_required
def proposta_pdf(request, pk):
    from django.utils import timezone

    from core.pdf import render_pdf

    proposta = get_object_or_404(
        queryset_da_empresa(Proposta.objects.select_related("cliente"), request.user), pk=pk
    )
    return render_pdf(
        "pdf/proposta.html",
        {
            "proposta": proposta,
            "itens": proposta.itens.all(),
            "fases_entrega": _fases_de_entrega(proposta),
            "empresa_nome": request.user.nome_empresa,
            "hoje": timezone.now(),
        },
        filename=f"proposta-{proposta.pk}.pdf", user=request.user,
    )


@require_POST
@login_required
def aprovar_proposta(request, pk):
    """Cliente aprovou. Sem projeto ainda, aprovar também o cria com as fases.

    Nascida dentro de um projeto (fase de proposta), ela já tem o seu — criar
    outro duplicaria o mesmo trabalho em duas fichas.
    """
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    if proposta.status == "aprovada":
        messages.info(request, "Esta proposta já está aprovada.")
        return redirect("proposta_detalhe", pk=proposta.pk)
    if proposta.status != "enviada":
        messages.info(request, "Envie a proposta ao cliente antes de registrar a aprovação.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    if proposta.projeto_gerado_id:
        proposta.status = "aprovada"
        proposta.save(update_fields=["status"])
        _aprovar_fase_da_proposta(proposta, request.user)
        proposta.cliente.fase = "ganho"
        proposta.cliente.save(update_fields=["fase"])
        messages.success(request, f"“{proposta.titulo}” aprovada pelo cliente.")
        from contratos.services import criar_contrato_da_proposta

        contrato = criar_contrato_da_proposta(proposta, request.user)
        return redirect("contrato_detalhe", pk=contrato.pk)

    horas_estimadas = sum(
        (item.horas_estimadas for item in proposta.itens.all()), Decimal("0")
    )
    with transaction.atomic():
        projeto = Projeto.objects.create(
            empresa=proposta.empresa,
            nome=proposta.titulo,
            cliente=proposta.cliente,
            tipo=proposta.tipo_projeto,
            valor_contratado=proposta.valor_total,
            horas_estimadas=horas_estimadas,
            data_inicio=timezone.localdate(),
            criado_por=request.user,
            origem_tipo="proposta",
            origem_id=proposta.pk,
        )
        from fases.models import montar_fases

        montar_fases(projeto)
        proposta.status = "aprovada"
        proposta.projeto_gerado = projeto
        proposta.save(update_fields=["status", "projeto_gerado"])
        # Move o cliente para "ganho" no funil.
        proposta.cliente.fase = "ganho"
        proposta.cliente.save(update_fields=["fase"])

    _aprovar_fase_da_proposta(proposta, request.user)
    from contratos.services import criar_contrato_da_proposta

    contrato = criar_contrato_da_proposta(proposta, request.user)
    messages.success(request, "Proposta aprovada. Revise a minuta do contrato.")
    return redirect("contrato_detalhe", pk=contrato.pk)


def _aprovar_fase_da_proposta(proposta, usuario):
    """A aprovação comercial libera a fase contratual, não o projeto técnico."""
    from fases.models import Fase

    fase = proposta.projeto_gerado.fases.filter(chave="proposta").first()
    if fase and fase.status != Fase.APROVADA:
        fase.status = Fase.APROVADA
        fase.respondida_em = timezone.now()
        fase.save(update_fields=["status", "respondida_em"])
        fase._abrir_seguintes(usuario)
        fase.projeto.tocar()
