"""Geração de PDF a partir de templates HTML (WeasyPrint)."""

import base64
import mimetypes

from django.http import HttpResponse
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string


def _bloquear_recurso_externo(url, timeout=10, ssl_context=None):
    """PDFs do A.R.Q. não precisam buscar URLs; bloquear evita SSRF/leitura local."""
    if url.startswith("data:image/"):
        from weasyprint import default_url_fetcher

        return default_url_fetcher(url, timeout=timeout, ssl_context=ssl_context)
    raise ValueError(f"Recurso externo bloqueado na geração de PDF: {url!r}")


def _identidade_pdf(user):
    """Embute a marca no HTML: preserva transparência e não abre acesso a arquivos."""
    from core.tenancy import obter_empresa_ativa_usuario

    empresa = obter_empresa_ativa_usuario(user)
    dados = {"empresa_nome": empresa.nome if empresa else user.nome_empresa}
    if empresa and empresa.logo:
        try:
            with empresa.logo.open("rb") as arquivo:
                conteudo = base64.b64encode(arquivo.read()).decode("ascii")
            mime = mimetypes.guess_type(empresa.logo.name)[0] or "image/png"
            dados["empresa_logo_data_uri"] = f"data:{mime};base64,{conteudo}"
            dados["empresa_logo_alt"] = f"Logo de {dados['empresa_nome']}"
        except (OSError, ValueError):
            pass
    if "empresa_logo_data_uri" not in dados:
        marca_app = finders.find("img/arq-mark.svg")
        if marca_app:
            try:
                with open(marca_app, "rb") as arquivo:
                    conteudo = base64.b64encode(arquivo.read()).decode("ascii")
                dados["empresa_logo_data_uri"] = f"data:image/svg+xml;base64,{conteudo}"
                dados["empresa_logo_alt"] = "A.R.Q."
                dados["usando_logo_app"] = True
            except OSError:
                pass
    return dados


def render_pdf(template_name, context, filename="documento.pdf", user=None):
    from weasyprint import HTML

    contexto = dict(context)
    if user is not None:
        contexto.update(_identidade_pdf(user))
    html = render_to_string(template_name, contexto)
    pdf_bytes = HTML(string=html, url_fetcher=_bloquear_recurso_externo).write_pdf()
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
