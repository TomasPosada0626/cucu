from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..errors import ValidationError

support_bp = Blueprint("support", __name__)


def _support_service():
    return current_app.config["support_service"]


@support_bp.post("/api/v3/ratings")
def create_rating():
    payload = request.get_json(silent=True) or {}
    usuario_id = payload.get("usuario") or payload.get("usuario_id")
    autor_id = payload.get("autor") or payload.get("autor_id")
    rating = _support_service().create_rating(
        usuario_id=usuario_id,
        autor_id=autor_id,
        puntuacion=payload.get("puntuacion"),
        comentario=payload.get("comentario"),
    )
    return jsonify({"data": rating}), 201


@support_bp.get("/api/v3/ratings")
def list_ratings():
    usuario_id = request.args.get("usuario") or request.args.get("usuario_id")
    if usuario_id is None:
        raise ValidationError("El parametro usuario es obligatorio")
    ratings = _support_service().list_ratings(usuario_id=usuario_id)
    return jsonify({"data": ratings}), 200


@support_bp.post("/api/v3/trust/certificates")
def upsert_certificate():
    payload = request.get_json(silent=True) or {}
    usuario_id = payload.get("usuario") or payload.get("usuario_id")
    cert = _support_service().upsert_certificate(
        usuario_id=usuario_id,
        archivo_url=payload.get("archivo_url"),
        fecha_emision=payload.get("fecha_emision"),
        estado_verificacion=bool(payload.get("estado_verificacion", False)),
    )
    return jsonify({"data": cert}), 200


@support_bp.get("/api/v3/trust/certificates")
def get_certificate():
    usuario_id = request.args.get("usuario") or request.args.get("usuario_id")
    if usuario_id is None:
        raise ValidationError("El parametro usuario es obligatorio")
    cert = _support_service().get_certificate(usuario_id=usuario_id)
    return jsonify({"data": cert}), 200


@support_bp.post("/api/v3/transactions")
def upsert_transaction():
    payload = request.get_json(silent=True) or {}
    pedido_id = payload.get("pedido") or payload.get("pedido_id")
    tx = _support_service().upsert_transaction(
        pedido_id=pedido_id,
        fecha_cierre=payload.get("fecha_cierre"),
        estado=payload.get("estado"),
        distancia_validacion_metros=payload.get("distancia_validacion_metros") or 0,
    )
    return jsonify({"data": tx}), 200


@support_bp.get("/api/v3/transactions")
def get_transaction():
    pedido_id = request.args.get("pedido") or request.args.get("pedido_id")
    if pedido_id is None:
        raise ValidationError("El parametro pedido es obligatorio")
    tx = _support_service().get_transaction(pedido_id=pedido_id)
    return jsonify({"data": tx}), 200


@support_bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
