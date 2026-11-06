import secrets

from django.conf import settings


class PermissionsPolicyMiddleware:
    """Desliga no navegador as APIs sensíveis que o app não usa.

    Sem o cabeçalho, um script injetado (ou um iframe de terceiro) pode pedir
    câmera, microfone, localização etc. O app não usa nenhuma delas, então o
    padrão é `()` (ninguém, nem a própria origem). `setdefault` respeita uma
    view que precise de outro valor.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        politica = getattr(settings, "PERMISSIONS_POLICY", "")
        if politica:
            response.setdefault("Permissions-Policy", politica)
        return response


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce
        response = self.get_response(request)
        if getattr(settings, "ENABLE_CSP", False) and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = settings.CONTENT_SECURITY_POLICY.format(
                nonce=nonce
            )
        return response
