from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..errors import ValidationError
from ..rate_limit import rate_limited

auth_bp = Blueprint("auth", __name__)

# Mismo presupuesto que el scope 'auth' del monolito Django: es el objetivo
# de fuerza bruta mas obvio (login/registro/refresh/reset de password).
_AUTH_RATE_LIMIT = {"max_requests": 10, "window_seconds": 60}


def _auth_service():
    return current_app.config["auth_service"]


def _payload() -> dict:
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("El cuerpo de la solicitud debe ser JSON valido")
    return payload


def _bearer_token() -> str:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        raise ValidationError("Authorization Bearer token requerido")
    return header.split(" ", 1)[1].strip()


@auth_bp.post("/api/v3/auth/register")
@rate_limited(**_AUTH_RATE_LIMIT)
def register():
    data = _payload()
    result = _auth_service().register(
        username=data.get("username"),
        email=data.get("email"),
        password=data.get("password"),
    )
    return jsonify({"data": result}), 201


@auth_bp.post("/api/v3/auth/login")
@rate_limited(**_AUTH_RATE_LIMIT)
def login():
    data = _payload()
    result = _auth_service().login(email=data.get("email"), password=data.get("password"))
    return jsonify({"data": result}), 200


@auth_bp.post("/api/v3/auth/refresh")
@rate_limited(**_AUTH_RATE_LIMIT)
def refresh():
    data = _payload()
    result = _auth_service().refresh(refresh_token=data.get("refresh_token"))
    return jsonify({"data": result}), 200


@auth_bp.get("/api/v3/auth/me")
def me():
    token = _bearer_token()
    result = _auth_service().me(access_token=token)
    return jsonify({"data": result}), 200


@auth_bp.post("/api/v3/auth/password-reset")
@rate_limited(**_AUTH_RATE_LIMIT)
def password_reset():
    data = _payload()
    result = _auth_service().reset_password(email=data.get("email"), new_password=data.get("new_password"))
    return jsonify({"data": result}), 200


@auth_bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
