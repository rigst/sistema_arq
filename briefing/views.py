from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.tenancy import queryset_da_empresa
from projetos.models import Projeto

from .forms import AmbienteForm, BriefingForm
from .models import AmbientePrograma, Briefing


def _get_briefing(request, projeto_pk):
    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.all(), request.user), pk=projeto_pk
    )
    briefing, _ = Briefing.objects.get_or_create(
        projeto=projeto, defaults={"empresa": projeto.empresa, "criado_por": request.user}
    )
    return projeto, briefing


@login_required
def editar_briefing(request, projeto_pk):
    """Rota antiga dos "blocos NBR", que agora moram na mesma tela do roteiro.

    Eram três telas para uma conversa só — roteiro de perguntas, blocos e
    programa de necessidades — e a pessoa precisava saber em qual delas cada
    coisa tinha sido escrita.
    """
    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.all(), request.user), pk=projeto_pk
    )
    return redirect("briefing_responder", projeto_pk=projeto.pk)


def _programa(request, projeto, briefing):
    """O bloco do programa, para trocar no lugar sem recarregar a página."""
    ambientes = list(briefing.ambientes.all())
    return render(
        request,
        "briefing/_programa.html",
        {
            "projeto": projeto,
            "ambientes": ambientes,
            "area_programa": sum(a.area_aprox or 0 for a in ambientes) or None,
            "editando": True,
        },
    )


@require_POST
@login_required
def adicionar_ambiente(request, projeto_pk):
    projeto, briefing = _get_briefing(request, projeto_pk)
    form = AmbienteForm(request.POST)
    if form.is_valid():
        ambiente = form.save(commit=False)
        ambiente.briefing = briefing
        ambiente.empresa = projeto.empresa
        ambiente.save()
    if request.headers.get("HX-Request"):
        return _programa(request, projeto, briefing)
    return redirect("briefing_responder", projeto_pk=projeto.pk)


@require_POST
@login_required
def remover_ambiente(request, pk):
    ambiente = get_object_or_404(
        queryset_da_empresa(AmbientePrograma.objects.all(), request.user), pk=pk
    )
    briefing = ambiente.briefing
    ambiente.delete()
    if request.headers.get("HX-Request"):
        return _programa(request, briefing.projeto, briefing)
    return redirect("briefing_responder", projeto_pk=briefing.projeto_id)


# =====================================================================
# Seção de briefings — templates, aplicação ao projeto e apoio de IA
# =====================================================================

from django.http import Http404  # noqa: E402

from core.tenancy import obter_grupo_empresa_ou_erro  # noqa: E402

from .forms import TemplateBriefingForm  # noqa: E402
from .models import (  # noqa: E402
    OpcaoPergunta,
    PerguntaTemplate,
    RespostaBriefing,
    TemplateBriefing,
)
from .services import perguntas_por_bloco, semear_templates_padrao  # noqa: E402


def _meus_templates(user):
    return queryset_da_empresa(TemplateBriefing.objects.all(), user)


@login_required
def templates_lista(request):
    return redirect("modelos")


@require_POST
@login_required
def semear_padroes(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    criados = semear_templates_padrao(grupo, request.user)
    if criados:
        messages.success(
            request, f"{len(criados)} roteiro(s) prontos adicionados. Edite à vontade."
        )
    else:
        messages.info(request, "Os roteiros prontos já estavam cadastrados.")
    return redirect("modelos")


@require_POST
@login_required
def template_novo(request):
    form = TemplateBriefingForm(request.POST)
    if form.is_valid():
        template = form.save(commit=False)
        template.empresa = obter_grupo_empresa_ou_erro(request.user)
        template.criado_por = request.user
        template.ativo = True
        template.save()
        messages.success(request, "Roteiro criado. Agora inclua as perguntas.")
        return redirect("briefing_template_detalhe", pk=template.pk)
    messages.error(request, "Dê um nome ao roteiro.")
    return redirect("modelos")


@login_required
def template_detalhe(request, pk):
    template = get_object_or_404(_meus_templates(request.user), pk=pk)
    if request.method == "POST":
        form = TemplateBriefingForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, "Roteiro salvo.")
            return redirect("briefing_template_detalhe", pk=template.pk)
    else:
        form = TemplateBriefingForm(instance=template)
    blocos = perguntas_por_bloco(template)
    for bloco in blocos:
        for pergunta in bloco["perguntas"]:
            pergunta.opcoes_texto = "\n".join(
                pergunta.opcoes.values_list("texto", flat=True)
            )
    return render(
        request,
        "briefing/template_detalhe.html",
        {
            "template": template,
            "form": form,
            "blocos": blocos,
            "tipos": PerguntaTemplate.TIPO_CHOICES,
        },
    )


@require_POST
@login_required
def template_add_pergunta(request, pk):
    template = get_object_or_404(_meus_templates(request.user), pk=pk)
    texto = (request.POST.get("texto") or "").strip()
    if not texto:
        messages.error(request, "Escreva a pergunta.")
        return redirect("briefing_template_detalhe", pk=template.pk)

    pergunta = PerguntaTemplate(
        empresa=template.empresa,
        template=template,
        ordem=template.perguntas.count(),
    )
    _preencher_pergunta(pergunta, request.POST)
    messages.success(request, "Pergunta incluída.")
    return redirect("briefing_template_detalhe", pk=template.pk)


def _preencher_pergunta(pergunta, dados):
    pergunta.texto = (dados.get("texto") or "").strip()
    pergunta.bloco = (dados.get("bloco") or "").strip()
    tipo = dados.get("tipo")
    pergunta.tipo = tipo if tipo in dict(PerguntaTemplate.TIPO_CHOICES) else "opcao"
    pergunta.ajuda = (dados.get("ajuda") or "").strip()
    pergunta.save()
    pergunta.opcoes.all().delete()
    linhas = [linha.strip() for linha in (dados.get("opcoes") or "").splitlines() if linha.strip()]
    OpcaoPergunta.objects.bulk_create(
        [
            OpcaoPergunta(
                empresa=pergunta.empresa,
                pergunta=pergunta,
                texto=linha,
                ordem=ordem,
            )
            for ordem, linha in enumerate(linhas)
        ]
    )


@require_POST
@login_required
def template_editar_pergunta(request, pk):
    pergunta = get_object_or_404(
        queryset_da_empresa(
            PerguntaTemplate.objects.select_related("template"), request.user
        ),
        pk=pk,
    )
    if not (request.POST.get("texto") or "").strip():
        messages.error(request, "Escreva a pergunta.")
    else:
        _preencher_pergunta(pergunta, request.POST)
        messages.success(request, "Pergunta atualizada.")
    return redirect("briefing_template_detalhe", pk=pergunta.template_id)


@require_POST
@login_required
def template_remove_pergunta(request, pk):
    pergunta = get_object_or_404(
        queryset_da_empresa(PerguntaTemplate.objects.all(), request.user), pk=pk
    )
    template_pk = pergunta.template_id
    pergunta.delete()
    return redirect("briefing_template_detalhe", pk=template_pk)


@require_POST
@login_required
def template_remover(request, pk):
    template = get_object_or_404(_meus_templates(request.user), pk=pk)
    template.delete()
    messages.success(request, "Roteiro removido.")
    return redirect("modelos")


@require_POST
@login_required
def aplicar_template(request, projeto_pk):
    """Vincula um roteiro ao briefing do projeto. Não apaga respostas já dadas —
    trocar de roteiro em cima da hora não pode custar o que já foi anotado."""
    projeto, briefing = _get_briefing(request, projeto_pk)
    template = get_object_or_404(_meus_templates(request.user), pk=request.POST.get("template"))
    request.session[f"briefing_template_{briefing.pk}"] = template.pk
    messages.success(request, f"Roteiro “{template.nome}” aberto para este projeto.")
    return redirect("briefing_responder", projeto_pk=projeto.pk)


@login_required
def responder(request, projeto_pk):
    projeto, briefing = _get_briefing(request, projeto_pk)
    semear_templates_padrao(projeto.empresa, request.user)
    template_pk = request.session.get(f"briefing_template_{briefing.pk}")
    template = _meus_templates(request.user).filter(pk=template_pk).first()
    if template is None:
        # Sem escolha explícita, abre o roteiro do tipo do projeto — abrir o de
        # loja num projeto residencial faz a pessoa achar que errou de tela.
        ativos = _meus_templates(request.user).filter(ativo=True)
        template = (
            ativos.filter(tipo_projeto=projeto.tipo).first()
            or ativos.filter(tipo_projeto="").first()
            or ativos.first()
        )
    if template is None:
        messages.info(request, "Nenhum roteiro cadastrado ainda. Comece pelos prontos.")
        return redirect("briefing_templates")

    if request.method == "POST":
        _salvar_respostas(request, briefing, template)
        form_blocos = BriefingForm(request.POST, instance=briefing)
        if form_blocos.is_valid():
            form_blocos.save()
        messages.success(request, f"Briefing de {projeto.nome} salvo.")
        # Briefing salvo é briefing pronto: o passo seguinte é a proposta, e
        # devolver para a mesma tela faria a pessoa procurar onde continuar.
        fase = projeto.fases.filter(chave="briefing").first()
        if fase is not None:
            fase.concluir_sem_aprovacao(request.user)
        proposta = projeto.fases.filter(chave="proposta").first()
        if proposta is not None:
            from propostas.views import criar_proposta_do_projeto

            rascunho = criar_proposta_do_projeto(projeto, request.user)
            return redirect("proposta_detalhe", pk=rascunho.pk)
        return redirect("projeto_detalhe", pk=projeto.pk)

    respostas = {r.pergunta_id: r for r in briefing.respostas.prefetch_related("opcoes")}
    blocos = perguntas_por_bloco(template)
    for bloco in blocos:
        respondidas = 0
        for pergunta in bloco["perguntas"]:
            resposta = respostas.get(pergunta.pk)
            pergunta.resposta_texto = resposta.texto if resposta else ""
            pergunta.marcadas = {o.pk for o in resposta.opcoes.all()} if resposta else set()
            if pergunta.resposta_texto or pergunta.marcadas:
                respondidas += 1
        # Em leitura, bloco sem nenhuma resposta vira título solto no vazio.
        bloco["respondidas"] = respondidas

    ambientes = list(briefing.ambientes.all())
    area_programa = sum(a.area_aprox or 0 for a in ambientes) or None

    # Briefing já respondido abre em leitura. Formulário longo aberto por padrão
    # convida a mexer no que já estava decidido, e some com a visão do conjunto.
    respondido = briefing.respostas.exists()
    editando = request.GET.get("editar") == "1" or not respondido

    return render(
        request,
        "briefing/responder.html",
        {
            "projeto": projeto,
            "briefing": briefing,
            "template": template,
            "templates": _meus_templates(request.user).filter(ativo=True),
            "blocos": blocos,
            "form_blocos": BriefingForm(instance=briefing),
            "ambientes": ambientes,
            "area_programa": area_programa,
            "form_ambiente": AmbienteForm(),
            "editando": editando,
            "respondido": respondido,
        },
    )


@login_required
def briefing_pdf(request, projeto_pk):
    from core.pdf import render_pdf

    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.select_related("cliente"), request.user),
        pk=projeto_pk,
    )
    briefing = get_object_or_404(Briefing.objects.all(), projeto=projeto)
    blocos = []
    por_nome = {}
    for resposta in briefing.respostas.select_related("pergunta").prefetch_related("opcoes"):
        nome = resposta.pergunta.bloco or "Geral"
        if nome not in por_nome:
            por_nome[nome] = {"nome": nome, "respostas": []}
            blocos.append(por_nome[nome])
        por_nome[nome]["respostas"].append(resposta)
    return render_pdf(
        "pdf/briefing.html",
        {
            "projeto": projeto,
            "briefing": briefing,
            "blocos": blocos,
            "ambientes": briefing.ambientes.all(),
            "empresa_nome": request.user.nome_empresa,
        },
        filename=f"briefing-{projeto.pk}.pdf",
    )


def _salvar_respostas(request, briefing, template):
    for pergunta in template.perguntas.all():
        marcadas = request.POST.getlist(f"p{pergunta.pk}")
        texto = (request.POST.get(f"t{pergunta.pk}") or "").strip()
        if not marcadas and not texto:
            RespostaBriefing.objects.filter(briefing=briefing, pergunta=pergunta).delete()
            continue
        resposta, _ = RespostaBriefing.objects.update_or_create(
            briefing=briefing,
            pergunta=pergunta,
            defaults={"empresa": briefing.empresa, "texto": texto},
        )
        opcoes = pergunta.opcoes.filter(pk__in=[m for m in marcadas if m.isdigit()])
        resposta.opcoes.set(opcoes)
