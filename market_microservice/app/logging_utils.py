from __future__ import annotations

import json
import logging
import os
import uuid
from contextvars import ContextVar

from flask import Flask, g, request

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIDLogFilter(logging.Filter):
    """Injects the in-flight request's id into every log record, same
    correlation pattern as the Django monolith's RequestIDMiddleware."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line, no new dependency - mirrors
    common/infrastructure/logging.py on the Django side, so a solo dev
    reading `docker compose logs` sees the same shape everywhere."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _init_sentry(app: Flask) -> None:
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=0.1,
        send_default_pii=False,
    )


def configure_structured_logging(app: Flask) -> None:
    _init_sentry(app)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIDLogFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

    # Werkzeug's own request-line access log stays on the default text
    # formatter - noisy to force into JSON and duplicates what the app's own
    # logger already records with a request_id attached.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    @app.before_request
    def _assign_request_id() -> None:
        incoming = (request.headers.get("X-Request-ID") or "").strip()[:64]
        request_id = incoming or uuid.uuid4().hex[:12]
        g.request_id = request_id
        _request_id_ctx.set(request_id)

    @app.after_request
    def _echo_request_id(response):
        response.headers.setdefault("X-Request-ID", g.get("request_id", "-"))
        return response
