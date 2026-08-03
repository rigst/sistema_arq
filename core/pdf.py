"""Geração de PDF a partir de templates HTML (WeasyPrint)."""

from django.http import HttpResponse
from django.template.loader import render_to_string


def _bloquear_recurso_externo(url, timeout=10, ssl_context=None):
    """PDFs do A.R.Q. não precisam buscar URLs; bloquear evita SSRF/leitura local."""
    raise ValueError(f"Recurso externo bloqueado na geração de PDF: {url!r}")


def render_pdf(template_name, context, filename="documento.pdf"):
    from weasyprint import HTML

    html = render_to_string(template_name, context)
    pdf_bytes = HTML(string=html, url_fetcher=_bloquear_recurso_externo).write_pdf()
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
