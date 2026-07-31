from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .checklist import montar_checklist


@login_required
def onboarding(request):
    contexto = montar_checklist(request.user)
    return render(request, "onboarding/onboarding.html", contexto)
