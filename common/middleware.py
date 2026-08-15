import uuid

from django.core.cache import cache
from django.http import JsonResponse

from common.infrastructure.logging import set_request_id

CSP_DIRECTIVES = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://maps.googleapis.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: blob: https://*.googleapis.com https://*.gstatic.com https://*.ggpht.com; "
    "connect-src 'self' https://*.googleapis.com; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "base-uri 'self'"
)


class RequestIDMiddleware:
    """Genera un ID corto por request para correlacionar logs de una misma
    peticion (ver common/infrastructure/logging.py) y lo devuelve en
    X-Request-ID para poder cruzarlo con reportes de usuarios/soporte."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = (request.META.get("HTTP_X_REQUEST_ID") or "").strip()[:64]
        request_id = incoming or uuid.uuid4().hex[:12]
        request.request_id = request_id
        set_request_id(request_id)

        response = self.get_response(request)
        response.setdefault("X-Request-ID", request_id)
        return response


class SecurityHeadersMiddleware:
    """Content-Security-Policy y otros headers de defensa en profundidad.

    script-src/style-src necesitan 'unsafe-inline' porque los templates usan
    <script>/<style> inline en toda la app (sin nonces) - igual vale como capa
    extra: bloquea exfiltracion a dominios externos (connect-src) y carga de
    scripts/imagenes de origenes no confiables (script-src/img-src), que es el
    vector mas comun despues de un XSS reflejado o de un tercero comprometido.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CSP_DIRECTIVES)
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "same-origin")
        response.setdefault("Permissions-Policy", "geolocation=(self), camera=(), microphone=()")
        return response


ADMIN_LOGIN_PATH = "/admin/login/"
ADMIN_LOGIN_RATE_LIMIT = 10
ADMIN_LOGIN_RATE_WINDOW_SECONDS = 60


class AdminLoginRateLimitMiddleware:
    """El admin de Django usa su propia vista de login (no pasa por DRF), asi
    que el throttling de REST_FRAMEWORK no lo cubre. Sin esto, /admin/login/
    acepta intentos de password ilimitados por IP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.path == ADMIN_LOGIN_PATH:
            ip = request.META.get("REMOTE_ADDR", "unknown")
            key = f"admin_login_throttle_{ip}"
            attempts = cache.get(key, 0)
            if attempts >= ADMIN_LOGIN_RATE_LIMIT:
                return JsonResponse(
                    {"detail": "Demasiados intentos de inicio de sesión. Intenta de nuevo más tarde."},
                    status=429,
                )
            cache.set(key, attempts + 1, timeout=ADMIN_LOGIN_RATE_WINDOW_SECONDS)

        return self.get_response(request)
