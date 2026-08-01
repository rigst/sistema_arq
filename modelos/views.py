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

from briefing.models import TemplateBriefing
from contratos.models import ModeloContrato
from core.tenancy import queryset_da_empresa


@login_required
def indice(request):
    return render(
        request,
        "modelos/indice.html",
        {
            "briefings": queryset_da_empresa(
                TemplateBriefing.objects.prefetch_related("perguntas"), request.user
            ),
            "contratos": queryset_da_empresa(ModeloContrato.objects.all(), request.user),
        },
    )
