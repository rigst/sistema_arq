from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from decimal import Decimal, InvalidOperation

from core.contexto import projeto_do_pedido
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
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


@login_required
def lista_propostas(request):
    propostas = queryset_da_empresa(Proposta.objects.select_related("cliente"), request.user)
    # Vindo da ficha de um projeto, a lista chega já recortada nele.
    projeto = projeto_do_pedido(request)
    if projeto is not None:
        propostas = propostas.filter(projeto_gerado=projeto)
    return render(
        request, "propostas/lista.html", {"propostas": propostas, "projeto": projeto}
    )


@login_required
def nova_proposta(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    projeto = projeto_do_pedido(request)
    if request.method == "POST":
        form = PropostaForm(request.POST, user=request.user, projeto=projeto)
        if form.is_valid():
            proposta = form.save(commit=False)
            proposta.empresa = grupo
            proposta.criado_por = request.user
            proposta.hora_tecnica_aplicada = hora_tecnica_base(grupo)
            if projeto is not None:
                # Fecha o laço: a proposta nascida de um projeto aponta para ele,
                # senão o roteiro continuaria dizendo que falta proposta.
                proposta.projeto_gerado = projeto
            proposta.save()
            messages.success(
                request, "Proposta criada. Ajuste a hora técnica e adicione os ambientes."
            )
            return redirect("proposta_detalhe", pk=proposta.pk)
    else:
        form = PropostaForm(user=request.user, projeto=projeto)
    return render(request, "propostas/form.html", {"form": form, "projeto": projeto})


@login_required
def detalhe_proposta(request, pk):
    proposta = get_object_or_404(
        queryset_da_empresa(Proposta.objects.select_related("cliente"), request.user), pk=pk
    )
    fatores = queryset_da_empresa(FatorPrecificacao.objects.filter(ativo=True), request.user)
    selecionados = set(proposta.fatores.values_list("pk", flat=True))
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
        },
    )


@require_POST
@login_required
def definir_hora_tecnica(request, pk):
    """Usuário escolhe a hora técnica da proposta: valor manual livre e/ou fatores
    de projeto aplicados sobre a hora-base. Reprecifica os itens existentes."""
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    if proposta.projeto_gerado_id:
        messages.info(request, "Proposta já aprovada; a hora técnica está travada.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    fatores_ids = request.POST.getlist("fatores")
    fatores = list(
        queryset_da_empresa(FatorPrecificacao.objects.all(), request.user).filter(pk__in=fatores_ids)
    )
    proposta.fatores.set(fatores)

    valor_manual = request.POST.get("valor_manual", "").strip().replace(",", ".")
    if valor_manual:
        try:
            proposta.hora_tecnica_aplicada = Decimal(valor_manual)
        except (InvalidOperation, ValueError):
            messages.error(request, "Valor de hora técnica inválido.")
            return redirect("proposta_detalhe", pk=proposta.pk)
    else:
        proposta.hora_tecnica_aplicada = aplicar_fatores(
            hora_tecnica_base(proposta.empresa), fatores
        )

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
    escolhidos = set(request.POST.getlist("prontos"))
    if not escolhidos:
        messages.error(request, "Marque ao menos um item.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    ja_tem = {i.descricao for i in proposta.itens.all()}
    ordem = proposta.itens.count()
    criados = 0
    for _, itens in itens_prontos.por_grupo():
        for descricao, horas in itens:
            if descricao not in escolhidos or descricao in ja_tem:
                continue
            calc = precificar_etapa(
                proposta.empresa, horas, hora_tecnica=proposta.hora_tecnica_aplicada
            )
            ItemProposta.objects.create(
                empresa=proposta.empresa, proposta=proposta, descricao=descricao,
                horas_estimadas=horas, valor=calc["total"], ordem=ordem + criados,
            )
            criados += 1
    if criados:
        messages.success(request, f"{criados} item(ns) adicionados e precificados. Ajuste as horas.")
    else:
        messages.info(request, "Esses itens já estavam na proposta.")
    return redirect("proposta_detalhe", pk=proposta.pk)


@require_POST
@login_required
def adicionar_item(request, pk):
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
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
        messages.success(request, "Item precificado e adicionado.")
    else:
        messages.error(request, "Informe descrição e horas.")
    return redirect("proposta_detalhe", pk=proposta.pk)


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
            messages.success(request, f"“{item.descricao}” atualizado.")
            return _itens_ou_redirect(request, proposta)
        messages.error(request, "Informe descrição e horas.")
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
    return render(
        request, "propostas/_item_linha.html", {"item": item, "proposta": item.proposta}
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
    return _itens_ou_redirect(request, proposta)


@require_POST
@login_required
def finalizar_proposta(request, pk):
    """Fecha a proposta e a manda ao cliente. A partir daqui, ela não muda."""
    proposta = get_object_or_404(queryset_da_empresa(Proposta.objects.all(), request.user), pk=pk)
    if not proposta.editavel:
        messages.info(request, "Esta proposta já foi enviada.")
        return redirect("proposta_detalhe", pk=proposta.pk)
    if not proposta.itens.exists():
        messages.error(request, "Uma proposta sem itens não tem o que enviar.")
        return redirect("proposta_detalhe", pk=proposta.pk)

    proposta.status = "enviada"
    proposta.save(update_fields=["status"])
    messages.success(
        request, f"“{proposta.titulo}” enviada ao cliente por R$ {proposta.valor_total}."
    )
    return redirect("proposta_detalhe", pk=proposta.pk)


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
            "empresa_nome": request.user.nome_empresa,
            "hoje": timezone.now(),
        },
        filename=f"proposta-{proposta.pk}.pdf",
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

    if proposta.projeto_gerado_id:
        proposta.status = "aprovada"
        proposta.save(update_fields=["status"])
        proposta.cliente.fase = "ganho"
        proposta.cliente.save(update_fields=["fase"])
        messages.success(request, f"“{proposta.titulo}” aprovada pelo cliente.")
        return redirect("proposta_detalhe", pk=proposta.pk)

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

    messages.success(request, "Proposta aprovada. Projeto criado com as etapas.")
    return redirect("projeto_detalhe", pk=projeto.pk)
