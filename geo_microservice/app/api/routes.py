from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..errors import ValidationError
from ..geocoding_service import GeocodingService
from ..routing_service import RouteService

geo_bp = Blueprint("geo", __name__)


def _payload() -> dict:
    return request.get_json(silent=True) or {}


@geo_bp.route("/geocode", methods=["GET", "POST"])
@geo_bp.route("/api/v2/geocode", methods=["GET", "POST"])
def geocode_address():
    data = _payload() if request.method == "POST" else request.args
    direccion_texto = (data.get("direccion_texto") or data.get("q") or "").strip()
    if not direccion_texto:
        raise ValidationError("La direccion es requerida")

    loc = GeocodingService().geocode_address(direccion_texto=direccion_texto)
    return jsonify({"direccion_texto": loc.direccion_texto, "latitud": float(loc.latitud), "longitud": float(loc.longitud)}), 200


@geo_bp.route("/geocode/suggest", methods=["GET", "POST"])
@geo_bp.route("/api/v2/geocode/suggest", methods=["GET", "POST"])
def suggest_addresses():
    data = _payload() if request.method == "POST" else request.args
    query = (data.get("q") or "").strip()
    try:
        limit = int(data.get("limit") or 5)
    except (TypeError, ValueError) as exc:
        raise ValidationError("El limite debe ser un entero") from exc

    items = GeocodingService().suggest_addresses(query=query, limit=limit)
    return jsonify({"items": items}), 200


@geo_bp.route("/route", methods=["GET", "POST"])
@geo_bp.route("/api/v2/route", methods=["GET", "POST"])
def get_route():
    data = _payload() if request.method == "POST" else request.args
    coords = (data.get("coords") or "").strip()
    if not coords:
        raise ValidationError("Las coordenadas son requeridas")

    route = RouteService().get_route(coords=coords)
    if not route:
        return jsonify({"detail": "No fue posible consultar el servicio de rutas"}), 502
    return jsonify(route), 200


@geo_bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
