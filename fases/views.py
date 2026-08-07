import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto
from tarefas.models import Tarefa

from . import catalogo
from .forms import (
    ArquivoDaFaseForm,
    FaseTarefaForm,
    LembreteForm,
    RenomearArquivoForm,
    RespostaClienteForm,
)
from .models import Fase, Lembrete, criar_complementares_avulsos, montar_fases
from .services import garantir_tarefas_da_fase


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
    if fase.chave == "contrato":
        return _fase_contrato(request, fase)
    garantir_tarefas_da_fase(fase, request.user)
    arquivos = list(fase.arquivos.select_related("criado_por").order_by("-criado_em"))
    tarefas = fase.tarefas.all()
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
            "tarefas": tarefas,
            "tarefas_horas": tarefas.aggregate(total=Sum("horas_previstas"))["total"] or 0,
            "form_tarefa": FaseTarefaForm(form_id=f"nova-tarefa-{fase.pk}"),
            "fases_projeto": fase.projeto.fases.all(),
        },
    )


def _fase_proposta(request, fase):
    """A fase abre diretamente na proposta completa."""
    from propostas.views import criar_proposta_do_projeto

    proposta = criar_proposta_do_projeto(fase.projeto, request.user)
    return redirect("proposta_detalhe", pk=proposta.pk)


def _fase_contrato(request, fase):
    """O contrato só fica acessível quando a proposta já foi aprovada."""
    contrato = fase.projeto.contratos.order_by("-criado_em").first()
    if contrato is not None:
        return redirect("contrato_detalhe", pk=contrato.pk)
    return redirect(f"{reverse('contrato_novo')}?projeto={fase.projeto_id}")


# ---------------------------------------------------------------- fluxo


@require_POST
@login_required
def enviar(request, pk):
    fase = get_object_or_404(_minhas(request.user), pk=pk)
    if fase.chave in {"proposta", "contrato"}:
        messages.info(request, "Envie e registre a resposta pelo documento desta fase.")
        return redirect(_voltar(fase))
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
    if fase.chave in {"proposta", "contrato"}:
        messages.info(request, "Registre a resposta pelo documento desta fase.")
        return redirect(_voltar(fase))
    form = RespostaClienteForm(request.POST)
    parecer = form.cleaned_data["parecer"] if form.is_valid() else ""
    aprovada = request.POST.get("decisao") == "aprovar"
    if fase.registrar_resposta(aprovada, parecer, request.user):
        if aprovada:
            messages.success(
                request,
                f"Cliente aprovou {fase.nome} de {fase.projeto.nome}. A próxima fase está liberada.",
            )
            proxima = (
                fase.projeto.fases.filter(ordem__gt=fase.ordem, status=Fase.EM_ELABORACAO)
                .order_by("ordem", "id")
                .first()
            )
            if proxima is not None:
                return redirect("fase_detalhe", pk=proxima.pk)
        else:
            messages.success(
                request, f"Cliente pediu ajustes em {fase.nome} de {fase.projeto.nome}."
            )
    return redirect(_voltar(fase))


def _tarefa_da_fase(user, pk):
    return get_object_or_404(
        queryset_da_empresa(Tarefa.objects.select_related("fase", "projeto"), user),
        pk=pk,
        fase__isnull=False,
    )


def _tarefas_ou_redirect(request, fase, form=None):
    if request.headers.get("HX-Request"):
        tarefas = fase.tarefas.all()
        return render(
            request,
            "fases/_tarefas.html",
            {
                "fase": fase,
                "tarefas": tarefas,
                "tarefas_horas": tarefas.aggregate(total=Sum("horas_previstas"))["total"] or 0,
                "form_tarefa": form or FaseTarefaForm(form_id=f"nova-tarefa-{fase.pk}"),
            },
        )
    return redirect(_voltar(fase) + "#tarefas-fase")


@require_POST
@login_required
def adicionar_tarefa(request, pk):
    fase = get_object_or_404(_minhas(request.user), pk=pk)
    form = FaseTarefaForm(request.POST, form_id=f"nova-tarefa-{fase.pk}")
    if form.is_valid():
        tarefa = form.save(commit=False)
        tarefa.empresa = fase.empresa
        tarefa.criado_por = request.user
        tarefa.projeto = fase.projeto
        tarefa.fase = fase
        maior_ordem = fase.tarefas.aggregate(maior=Max("ordem"))["maior"]
        tarefa.ordem = 0 if maior_ordem is None else maior_ordem + 1
        tarefa.save()
        messages.success(request, "Tarefa adicionada.")
        return _tarefas_ou_redirect(request, fase)
    messages.error(request, "Informe a tarefa, a data e as horas previstas.")
    return _tarefas_ou_redirect(request, fase, form)


@login_required
def editar_tarefa(request, pk):
    tarefa = _tarefa_da_fase(request.user, pk)
    form_id = f"editar-tarefa-{tarefa.pk}"
    if request.method == "POST":
        form = FaseTarefaForm(request.POST, instance=tarefa, form_id=form_id)
        if form.is_valid():
            form.save()
            messages.success(request, "Tarefa atualizada.")
            return _tarefas_ou_redirect(request, tarefa.fase)
    else:
        form = FaseTarefaForm(instance=tarefa, form_id=form_id)
    return render(
        request,
        "fases/_tarefa_linha.html",
        {"fase": tarefa.fase, "tarefa": tarefa, "form_edicao": form},
    )


@login_required
def linha_tarefa(request, pk):
    tarefa = _tarefa_da_fase(request.user, pk)
    return render(request, "fases/_tarefa_linha.html", {"fase": tarefa.fase, "tarefa": tarefa})


@require_POST
@login_required
def alternar_tarefa(request, pk):
    tarefa = _tarefa_da_fase(request.user, pk)
    tarefa.status = "aberta" if tarefa.status == "concluida" else "concluida"
    tarefa.save(update_fields=["status"])
    return _tarefas_ou_redirect(request, tarefa.fase)


@require_POST
@login_required
def remover_tarefa(request, pk):
    tarefa = _tarefa_da_fase(request.user, pk)
    fase = tarefa.fase
    tarefa.delete()
    messages.success(request, "Tarefa excluída.")
    return _tarefas_ou_redirect(request, fase)


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
        f.chave
        for f in projeto.fases.filter(chave__startswith="comp_").exclude(chave=catalogo.CHAVE_LIVRE)
    }
    livres_marcados = set(request.POST.getlist("complementares_livres"))

    for chave in atuais - marcados:
        fase = projeto.fases.get(chave=chave)
        for arquivo in fase.arquivos.all():
            arquivo.arquivo.delete(save=False)
        fase.delete()

    for fase in projeto.fases.filter(chave=catalogo.CHAVE_LIVRE).exclude(pk__in=livres_marcados):
        for arquivo in fase.arquivos.all():
            arquivo.arquivo.delete(save=False)
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


@require_POST
@login_required
def alternar_favorito_arquivo(request, pk):
    arquivo = _arquivo_da_empresa(request.user, pk)
    if arquivo.fase_id is None:
        raise Http404
    arquivo.favorito = not arquivo.favorito
    arquivo.save(update_fields=["favorito"])

    if request.headers.get("HX-Request"):
        if request.headers.get("HX-Target") == "arquivos-principais":
            from projetos.views import contexto_arquivos_principais

            return render(
                request,
                "projetos/_arquivos_principais.html",
                contexto_arquivos_principais(arquivo.projeto),
            )
        return render(request, "fases/_arquivo_linha.html", {"a": arquivo})
    return redirect(_voltar(arquivo.fase))


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
        else reverse("projeto_detalhe", kwargs={"pk": arquivo.projeto_id})
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
    destino = (
        reverse("fase_detalhe", kwargs={"pk": fase.pk})
        if fase
        else reverse("projeto_detalhe", kwargs={"pk": arquivo.projeto_id})
    )
    titulo = arquivo.titulo
    arquivo.arquivo.delete(save=False)
    arquivo.delete()
    messages.success(request, f"Arquivo “{titulo}” removido.")
    return redirect(destino)
