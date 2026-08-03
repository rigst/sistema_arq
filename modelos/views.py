"""Os modelos reaproveitáveis do escritório, numa página só.

Roteiro de briefing e minuta de contrato são a mesma coisa do ponto de vista de
quem usa: texto que o escritório escreve uma vez e reaproveita em todo projeto.
Estavam em dois itens de menu distantes um do outro, e a pergunta "onde eu
guardo esse modelo?" tinha duas respostas — que é o mesmo que não ter nenhuma.

Esta view não cria modelo: ela reúne e manda para as telas que já existem,
onde a edição continua acontecendo.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from briefing.forms import TemplateBriefingForm
from briefing.models import TemplateBriefing
from briefing.services import semear_templates_padrao
from contratos.models import ModeloContrato
from contratos.services import garantir_modelos_padrao
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa


@login_required
def indice(request):
    grupo = obter_grupo_empresa_ou_erro(request.user)
    semear_templates_padrao(grupo, request.user)
    garantir_modelos_padrao(grupo, request.user)

    from briefing.templates_padrao import PADROES
    from contratos.modelos_padrao import MODELOS_PADRAO

    return render(
        request,
        "modelos/indice.html",
        {
            "briefings": queryset_da_empresa(
                TemplateBriefing.objects.prefetch_related("perguntas"), request.user
            ),
            "contratos": queryset_da_empresa(ModeloContrato.objects.all(), request.user),
            "form_briefing": TemplateBriefingForm(),
            "briefings_padrao": {modelo["nome"] for modelo in PADROES},
            "contratos_padrao": {modelo["nome"] for modelo in MODELOS_PADRAO},
        },
    )
