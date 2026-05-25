from __future__ import annotations

from django.conf import settings


class GlobalLanguageSwitcherMiddleware:
    """Injects a global language switcher script into every HTML response."""

    SCRIPT_MARKER = "cucu-i18n.js"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            return response

        if getattr(response, "streaming", False):
            return response

        content = response.content
        if not content:
            return response

        try:
            html = content.decode(response.charset or "utf-8")
        except Exception:
            return response

        if self.SCRIPT_MARKER in html:
            return response

        closing_body = html.lower().rfind("</body>")
        if closing_body == -1:
            return response

        static_url = settings.STATIC_URL
        if not static_url.startswith("/"):
            static_url = f"/{static_url}"
        if not static_url.endswith("/"):
            static_url = f"{static_url}/"

        script_tag = f'<script src="{static_url}js/cucu-i18n.js" defer></script>'
        html = f"{html[:closing_body]}{script_tag}{html[closing_body:]}"

        response.content = html.encode(response.charset or "utf-8")
        response["Content-Length"] = str(len(response.content))
        return response
