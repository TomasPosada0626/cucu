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
