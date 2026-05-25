from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..errors import ValidationError

notifications_bp = Blueprint("notifications", __name__)


def _notification_service():
    return current_app.config["notification_service"]


@notifications_bp.post("/api/v3/notifications")
def create_notification():
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("El cuerpo de la solicitud debe ser JSON valido")

    notification = _notification_service().create_notification(
        usuario_id=payload.get("usuario_id"),
        tipo=payload.get("tipo"),
        mensaje=payload.get("mensaje"),
    )
    return jsonify({"data": notification.to_dict()}), 201


@notifications_bp.get("/api/v3/notifications")
def get_user_notifications():
    usuario_id = request.args.get("usuario_id")
    if usuario_id is None:
        raise ValidationError("El usuario es obligatorio")
    notifications = _notification_service().get_user_notifications(usuario_id=int(usuario_id))
    return jsonify({"data": [item.to_dict() for item in notifications]}), 200


@notifications_bp.post("/api/v3/notifications/<int:notification_id>/read")
def mark_notification_as_read(notification_id: int):
    notification = _notification_service().mark_as_read(notification_id=notification_id)
    return jsonify({"data": notification.to_dict()}), 200


@notifications_bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
