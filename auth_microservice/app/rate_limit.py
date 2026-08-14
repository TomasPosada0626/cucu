from __future__ import annotations

import time
from collections import defaultdict
from functools import wraps
from threading import Lock

from flask import jsonify, request

# Rate limiting en memoria de proceso: el servicio corre con
# `gunicorn --workers 1 --threads 4` (ver Dockerfile), asi que un solo
# diccionario compartido entre threads es suficiente y no requiere Redis.
# Si el numero de workers cambia, esto deja de ser correcto y habria que
# mover el contador a un store compartido.
_hits: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _client_ident() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()


def rate_limited(*, max_requests: int, window_seconds: int):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            ident = _client_ident()
            key = f"{view_func.__name__}:{ident}"
            now = time.time()
            cutoff = now - window_seconds
            with _lock:
                hits = _hits[key]
                while hits and hits[0] < cutoff:
                    hits.pop(0)
                if len(hits) >= max_requests:
                    return (
                        jsonify({
                            "error": {
                                "code": "rate_limited",
                                "message": "Demasiados intentos. Intenta de nuevo en un momento.",
                            }
                        }),
                        429,
                    )
                hits.append(now)
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
