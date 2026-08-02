import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from . import catalogo
from .forms import (
    ArquivoDaFaseForm,
    LembreteForm,
    RenomearArquivoForm,
    RespostaClienteForm,
)
from .models import Fase, Lembrete, criar_complementares_avulsos, montar_fases


def _minhas(user):
    return queryset_da_empresa(
        Fase.objects.select_related("projeto", "projeto__cliente", "fornecedor"), user
    )


def _voltar(fase):
    return reverse("fase_detalhe", kwargs={"pk": fase.pk})


@login_required
def detalhe(request, pk):
    """A área de trabalho da fase: o que produzir, o material e o histórico."""
    fase = get_object_or_404(_minhas(request.user), pk=pk)
    if fase.bloqueada:
        messages.error(request, fase.impedimento)
        return redirect(reverse("projeto_detalhe", kwargs={"pk": fase.projeto_id}) + "#fases")
    if fase.chave == "briefing":
        # O briefing não tem material solto nem tarefa: ele É a conversa. Ter
        # uma tela intermediária com arquivos vazios só somava um clique.
        return redirect("briefing_responder", projeto_pk=fase.projeto_id)
    if fase.chave == "proposta":
        return _fase_proposta(request, fase)
    arquivos = list(fase.arquivos.select_related("criado_por").order_by("-criado_em"))
    return render(
        request,
        "fases/detalhe.html",
        {
            "fase": fase,
            "projeto": fase.projeto,
            "arquivos": arquivos,
            "imagens": [a for a in arquivos if a.eh_imagem],
            "form_arquivo": ArquivoDaFaseForm(),
            "form_registro": LembreteForm(),
            "form_resposta": RespostaClienteForm(),
            "fases_projeto": fase.projeto.fases.all(),
            "insumos": _insumos(fase),
        },
    )


def _fase_proposta(request, fase):
    """A fase de proposta e contrato, com as duas coisas na própria tela.

    Mandar para uma lista global de propostas e outra de contratos obrigava a
    voltar duas vezes para conferir se o que foi feito era daquele projeto.
    """
    from contratos.models import Contrato, ModeloContrato
    from propostas.models import Proposta

    projeto = fase.projeto
    proposta = getattr(projeto, "proposta_origem", None)
    contrato = projeto.contratos.order_by("-criado_em").first()
    return render(
        request,
        "fases/proposta.html",
        {
            "fase": fase,
            "projeto": projeto,
            "proposta": proposta,
            "contrato": contrato,
            "modelos": queryset_da_empresa(
                ModeloContrato.objects.filter(ativo=True), request.user
            ),
            "arquivos": list(fase.arquivos.select_related("criado_por").order_by("-criado_em")),
            "form_arquivo": ArquivoDaFaseForm(),
            "form_resposta": RespostaClienteForm(),
        },
    )


def _insumos(fase):
    """O que a fase anterior deixou pronto e esta consome.

    A partir do estudo preliminar, todo desenho parte do programa de
    necessidades. Ter que abrir outra tela para lembrar quantos dormitórios o
    cliente pediu é como o programa vira decorativo.
    """
    if fase.bloqueada:
        messages.error(request, fase.impedimento)
        return redirect(reverse("projeto_detalhe", kwargs={"pk": fase.projeto_id}) + "#fases")
    if fase.chave == "briefing":
        return None
    briefing = getattr(fase.projeto, "briefing", None)
    if briefing is None:
        return None
    ambientes = list(briefing.ambientes.all())
    total = sum(a.area_total or 0 for a in ambientes)
    return {
        "briefing": briefing,
        "ambientes": ambientes,
        "area_total": total or None,
        "referencias": briefing.referencias,
        "estilo": briefing.estilo,
        "restricoes": briefing.restricoes,
    }


# ---------------------------------------------------------------- fluxo


@require_POST
@login_required
def enviar(request, pk):
    fase = get_object_or_404(_minhas(request.user), pk=pk)
    if not fase.arquivos.exists():
        messages.error(
            request,
            "Anexe o material antes de enviar — é o material que o cliente vai aprovar.",
        )
    elif fase.enviar_ao_cliente(request.user):
        messages.success(request, f"{fase.nome} de {fase.projeto.nome} enviada ao cliente.")
    return redirect(_voltar(fase))


@require_POST
@login_required
def responder(request, pk):
    """Registra o que o cliente respondeu: aprovou ou pediu ajustes."""
    fase = get_object_or_404(_minhas(request.user), pk=pk)
    form = RespostaClienteForm(request.POST)
    parecer = form.cleaned_data["parecer"] if form.is_valid() else ""
    aprovada = request.POST.get("decisao") == "aprovar"
    if fase.registrar_resposta(aprovada, parecer, request.user):
        if aprovada:
            messages.success(request, f"Cliente aprovou {fase.nome} de {fase.projeto.nome}. A próxima fase está liberada.")
        else:
            messages.success(request, f"Cliente pediu ajustes em {fase.nome} de {fase.projeto.nome}.")
    return redirect(_voltar(fase))


@require_POST
@login_required
def concluir(request, pk):
    fase = get_object_or_404(_minhas(request.user), pk=pk)
    if fase.concluir_sem_aprovacao(request.user):
        messages.success(request, f"{fase.nome} de {fase.projeto.nome} concluída.")
    return redirect(_voltar(fase))


@require_POST
@login_required
def comentar(request, pk):
    fase = get_object_or_404(_minhas(request.user), pk=pk)
    form = LembreteForm(request.POST)
    if form.is_valid():
        registro = form.save(commit=False)
        registro.fase = fase
        registro.projeto = fase.projeto
        registro.empresa = fase.empresa
        registro.autor = request.user
        registro.save()
    else:
        messages.error(request, "Escreva o lembrete antes de fixar.")
    return redirect(f"{_voltar(fase)}#lembretes")


@require_POST
@login_required
def editar_lembrete(request, pk):
    lembrete = get_object_or_404(
        queryset_da_empresa(Lembrete.objects.select_related("fase", "projeto"), request.user),
        pk=pk,
    )
    destino = (
        reverse("fase_detalhe", kwargs={"pk": lembrete.fase_id})
        if lembrete.fase_id
        else reverse("projeto_detalhe", kwargs={"pk": lembrete.projeto_id})
    )
    form = LembreteForm(request.POST, instance=lembrete)
    if form.is_valid():
        form.save()
        messages.success(request, f"Lembrete de {lembrete.projeto.nome} editado.")
    else:
        messages.error(request, "O lembrete não pode ficar vazio.")
    return redirect(f"{destino}#lembretes")


@require_POST
@login_required
def remover_lembrete(request, pk):
    lembrete = get_object_or_404(
        queryset_da_empresa(Lembrete.objects.select_related("fase"), request.user), pk=pk
    )
    destino = (
        reverse("fase_detalhe", kwargs={"pk": lembrete.fase_id})
        if lembrete.fase_id
        else reverse("projeto_detalhe", kwargs={"pk": lembrete.projeto_id})
    )
    resumo = lembrete.texto[:60] + ("…" if len(lembrete.texto) > 60 else "")
    lembrete.delete()
    messages.success(request, f"Lembrete excluído: “{resumo}”.")
    return redirect(f"{destino}#lembretes")


@require_POST
@login_required
def lembrete_do_projeto(request, projeto_pk):
    """Lembrete que não é de fase nenhuma — vale para o projeto inteiro."""
    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.all(), request.user), pk=projeto_pk
    )
    form = LembreteForm(request.POST)
    if form.is_valid():
        lembrete = form.save(commit=False)
        lembrete.empresa = projeto.empresa
        lembrete.projeto = projeto
        lembrete.autor = request.user
        lembrete.save()
    else:
        messages.error(request, "Escreva o lembrete antes de fixar.")
    return redirect(reverse("projeto_detalhe", kwargs={"pk": projeto.pk}) + "#lembretes")


@require_POST
@login_required
def editar_complementares(request, projeto_pk):
    """Liga e desliga complementares de uma vez, pelo modal do projeto."""
    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.all(), request.user), pk=projeto_pk
    )
    marcados = set(request.POST.getlist("complementares"))
    atuais = {
        f.chave for f in projeto.fases.filter(chave__startswith="comp_").exclude(
            chave=catalogo.CHAVE_LIVRE
        )
    }

    # Desligar só o que está vazio: complementar com arquivo dentro guarda
    # trabalho, e apagar isso por engano num modal seria irreversível.
    for chave in atuais - marcados:
        fase = projeto.fases.get(chave=chave)
        if fase.arquivos.exists() or fase.status != Fase.NAO_INICIADA:
            messages.error(
                request,
                f"“{fase.nome}” já tem trabalho registrado — remova pela própria fase.",
            )
            continue
        fase.delete()

    montar_fases(projeto, complementares=marcados - atuais)
    criar_complementares_avulsos(projeto, request.POST.get("complementar_outro", ""))
    messages.success(request, f"Complementares de {projeto.nome} atualizados.")
    return redirect(reverse("projeto_detalhe", kwargs={"pk": projeto.pk}) + "#fases")


@require_POST
@login_required
def ativar_complementar(request, projeto_pk):
    """Liga um projeto complementar. São opcionais e entram sob demanda."""
    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.all(), request.user), pk=projeto_pk
    )
    chave = request.POST.get("chave", "")
    passo = catalogo.passo(chave)
    if passo is None or not passo.opcional:
        messages.error(request, "Complementar desconhecido.")
    elif montar_fases(projeto, complementares=[chave]):
        messages.success(request, f"{passo.nome} adicionado ao projeto.")
    else:
        messages.info(request, f"{passo.nome} já estava no projeto.")
    return redirect(reverse("projeto_detalhe", kwargs={"pk": projeto.pk}) + "#fases")


@require_POST
@login_required
def remover_complementar(request, pk):
    fase = get_object_or_404(_minhas(request.user), pk=pk)
    if not fase.complementar:
        messages.error(request, "Só complementar pode sair do projeto.")
        return redirect(_voltar(fase))
    projeto_pk = fase.projeto_id
    nome = fase.nome
    for arquivo in fase.arquivos.all():
        arquivo.arquivo.delete(save=False)
    fase.delete()
    messages.success(request, f"{nome} removido do projeto.")
    return redirect(reverse("projeto_detalhe", kwargs={"pk": projeto_pk}) + "#fases")


# ------------------------------------------------------------- arquivos


@require_POST
@login_required
def anexar(request, pk):
    fase = get_object_or_404(_minhas(request.user), pk=pk)
    form = ArquivoDaFaseForm(request.POST, request.FILES)
    if form.is_valid():
        arquivo = form.save(commit=False)
        arquivo.empresa = fase.empresa
        arquivo.projeto = fase.projeto
        arquivo.fase = fase
        arquivo.criado_por = request.user
        arquivo.save()
        messages.success(request, f"Arquivo “{arquivo.titulo}” anexado a {fase.nome}.")
    else:
        messages.error(request, "Confira o arquivo e o nome antes de anexar.")
    return redirect(_voltar(fase))


def _arquivo_da_empresa(user, pk):
    from arquivos.models import Arquivo

    return get_object_or_404(
        queryset_da_empresa(Arquivo.objects.select_related("fase"), user), pk=pk
    )


@login_required
def ver_arquivo(request, pk):
    """Serve o arquivo pelo sistema, e não pela pasta de mídia.

    Duas razões: o arquivo de um escritório não pode ficar acessível por URL
    adivinhada, e é aqui que dá para responder inline — o navegador abre PDF e
    imagem na aba em vez de baixar.
    """
    arquivo = _arquivo_da_empresa(request.user, pk)
    if not arquivo.arquivo:
        raise Http404
    tipo, _ = mimetypes.guess_type(arquivo.arquivo.name)
    nome = f"{arquivo.titulo}.{arquivo.extensao}" if arquivo.extensao else arquivo.titulo
    resposta = FileResponse(
        arquivo.arquivo.open("rb"),
        content_type=tipo or "application/octet-stream",
        as_attachment=not arquivo.visualizavel,
        filename=nome,
    )
    # Sem sniffing: arquivo enviado por terceiro não decide o próprio tipo.
    resposta["X-Content-Type-Options"] = "nosniff"
    return resposta


@login_required
def renomear_arquivo(request, pk):
    arquivo = _arquivo_da_empresa(request.user, pk)
    destino = (
        reverse("fase_detalhe", kwargs={"pk": arquivo.fase_id})
        if arquivo.fase_id
        else reverse("arquivos_lista")
    )
    if request.method == "POST":
        antigo = arquivo.titulo
        form = RenomearArquivoForm(request.POST, instance=arquivo)
        if form.is_valid():
            form.save()
            if antigo != arquivo.titulo:
                messages.success(request, f"Arquivo renomeado: “{antigo}” → “{arquivo.titulo}”.")
            else:
                messages.success(request, f"Arquivo “{arquivo.titulo}” atualizado.")
            return redirect(destino)
    else:
        form = RenomearArquivoForm(instance=arquivo)
    return render(
        request, "fases/renomear.html", {"form": form, "arquivo": arquivo, "destino": destino}
    )


@require_POST
@login_required
def remover_arquivo(request, pk):
    arquivo = _arquivo_da_empresa(request.user, pk)
    fase = arquivo.fase
    destino = reverse("fase_detalhe", kwargs={"pk": fase.pk}) if fase else reverse("arquivos_lista")
    titulo = arquivo.titulo
    arquivo.arquivo.delete(save=False)
    arquivo.delete()
    messages.success(request, f"Arquivo “{titulo}” removido.")
    return redirect(destino)
