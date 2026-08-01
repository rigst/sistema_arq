"""Contexto de projeto carregado pela URL.

O sistema tem muitos cadastros que só fazem sentido dentro de um projeto —
proposta, contrato, obra. Antes, cada um deles abria um formulário em branco no
meio do nada e o arquiteto redigitava cliente e projeto que o sistema já sabia.

A convenção é uma só: quem manda para um formulário desses acrescenta
``?projeto=<pk>``. O formulário chega preenchido e, ao salvar, a pessoa volta
para o projeto de onde saiu, em vez de cair numa lista global.
"""

from django.urls import reverse

from core.tenancy import queryset_da_empresa

PARAMETRO = "projeto"


def projeto_do_pedido(request):
    """O projeto indicado em ``?projeto=<pk>``, ou None.

    Silencioso de propósito: um pk inválido ou de outra empresa não é erro de
    página, é só ausência de contexto — o formulário abre em branco.
    """
    from projetos.models import Projeto

    pk = request.GET.get(PARAMETRO) or request.POST.get(PARAMETRO)
    if not pk:
        return None
    return (
        queryset_da_empresa(Projeto.objects.select_related("cliente"), request.user)
        .filter(pk=pk)
        .first()
    )


def com_projeto(url, projeto):
    """Acrescenta o contexto de projeto a uma URL já montada."""
    if projeto is None:
        return url
    pk = getattr(projeto, "pk", projeto)
    return f"{url}?{PARAMETRO}={pk}"


def url_no_projeto(nome, projeto, **kwargs):
    return com_projeto(reverse(nome, kwargs=kwargs) if kwargs else reverse(nome), projeto)


def voltar_para(projeto, padrao):
    """Para onde levar depois de salvar: o projeto de origem, se houver."""
    if projeto is None:
        return padrao
    return reverse("projeto_detalhe", kwargs={"pk": projeto.pk})
