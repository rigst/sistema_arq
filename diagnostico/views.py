from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .perguntas import PERGUNTAS, PONTOS_MAXIMO, avaliar


@require_http_methods(["GET", "POST"])
def diagnostico(request):
    """Ferramenta pública de topo de funil. Stateless: nada é armazenado."""
    resultado = None
    if request.method == "POST":
        respostas = {p["id"]: request.POST.get(p["id"]) for p in PERGUNTAS}
        pontos, faixa, descricao = avaliar(respostas)
        resultado = {
            "pontos": pontos,
            "maximo": PONTOS_MAXIMO,
            "percentual": round(pontos / PONTOS_MAXIMO * 100),
            "faixa": faixa,
            "descricao": descricao,
        }
    return render(
        request,
        "diagnostico/diagnostico.html",
        {"perguntas": PERGUNTAS, "resultado": resultado},
    )
