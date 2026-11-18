from django.conf import settings
from django.shortcuts import redirect

from . import rls
from .models import AuditLog, Consent


class RLSContextMiddleware:
    """Informa ao banco o usuário da requisição e limpa ao final (evita vazamento entre requisições)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        uid = user.pk if user is not None and user.is_authenticated else None
        rls.set_context(user_id=uid)
        try:
            return self.get_response(request)
        finally:
            rls.set_context()


class ConsentMiddleware:
    """Streamer precisa aceitar o termo LGPD (e passar pelo primeiro acesso) antes de usar o app."""

    ALLOWED_PREFIXES = ("/boas-vindas", "/entrar", "/accounts", "/sair", "/static", "/media", "/manifest", "/sw.js", "/offline")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not request.path.startswith(self.ALLOWED_PREFIXES):
            creator = getattr(user, "creator", None) if hasattr(user, "creator") else None
            if creator is not None and not Consent.objects.filter(user=user, version=settings.CONSENT_VERSION).exists():
                return redirect("/boas-vindas/")
        return self.get_response(request)


class AuditMiddleware:
    """Registra toda ação de escrita feita na área de gestão."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method == "POST"
            and request.path.startswith("/gestao")
            and request.user.is_authenticated
            and response.status_code < 400
        ):
            agency = getattr(request, "agency", None)
            AuditLog.objects.create(
                agency=agency,
                actor=request.user,
                action=f"POST {request.resolver_match.url_name if request.resolver_match else request.path}",
                target=request.path[:200],
                detail={k: v for k, v in request.POST.items() if k not in ("csrfmiddlewaretoken", "file")}  # sem arquivos
                if len(request.POST) < 40 else {},
            )
        return response
