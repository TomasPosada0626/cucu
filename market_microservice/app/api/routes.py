from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..errors import ValidationError

market_bp = Blueprint("market", __name__)


def _market_service():
    return current_app.config["market_service"]


def _payload() -> dict:
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("El cuerpo de la solicitud debe ser JSON valido")
    return payload


@market_bp.post("/api/v3/publications")
def create_publication():
    data = _payload()
    publication = _market_service().create_publication(
        autor_id=data.get("autor_id"),
        titulo=data.get("titulo"),
        descripcion=data.get("descripcion"),
        precio=data.get("precio"),
        direccion_texto=data.get("direccion_texto"),
    )
    return jsonify({"data": publication.to_dict()}), 201


@market_bp.get("/api/v3/publications")
def list_publications():
    items = _market_service().list_publications()
    return jsonify({"data": [i.to_dict() for i in items]}), 200


@market_bp.post("/api/v3/orders")
def create_order():
    data = _payload()
    order = _market_service().create_order(
        publicacion_id=data.get("publicacion_id"),
        comprador_id=data.get("comprador_id"),
        cantidad=data.get("cantidad"),
    )
    return jsonify({"data": order.to_dict()}), 201


@market_bp.get("/api/v3/orders")
def list_orders():
    orders = _market_service().list_orders()
    return jsonify({"data": [o.to_dict() for o in orders]}), 200


@market_bp.get("/api/v3/orders/<int:order_id>")
def get_order(order_id: int):
    order = _market_service().get_order(order_id=order_id)
    return jsonify({"data": order.to_dict()}), 200


@market_bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
