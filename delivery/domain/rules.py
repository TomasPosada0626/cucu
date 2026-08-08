from __future__ import annotations

from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo

from common.exceptions import ValidationError

PAYOUT_TIMEZONE = ZoneInfo("America/Bogota")

# Estados (duplicados aqui como strings simples para que este modulo no
# dependa del ORM; infrastructure/models.py es la fuente de verdad de los
# choices reales).
ASIGNADO = "ASIGNADO"
LLEGO_RECOGIDA = "LLEGO_RECOGIDA"
EN_CAMINO_ENTREGA = "EN_CAMINO_ENTREGA"
LLEGO_ENTREGA = "LLEGO_ENTREGA"
FINALIZADO = "FINALIZADO"

GEOFENCE_RADIUS_METERS = 120.0


def haversine_meters(*, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radio_tierra_m = 6_371_000.0
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 2 * radio_tierra_m * asin(sqrt(a))


def next_state_after_location_update(
    *,
    estado_actual: str,
    repartidor_lat: float,
    repartidor_lng: float,
    recogida_lat: float,
    recogida_lng: float,
    entrega_lat: float,
    entrega_lng: float,
    radius_m: float = GEOFENCE_RADIUS_METERS,
) -> str | None:
    """Reglas automaticas (por geolocalizacion). Devuelve el nuevo estado si
    corresponde una transicion automatica, o None si no cambia nada."""

    if estado_actual == ASIGNADO:
        distancia = haversine_meters(
            lat1=repartidor_lat, lng1=repartidor_lng, lat2=recogida_lat, lng2=recogida_lng
        )
        if distancia <= radius_m:
            return LLEGO_RECOGIDA
        return None

    if estado_actual == EN_CAMINO_ENTREGA:
        distancia = haversine_meters(
            lat1=repartidor_lat, lng1=repartidor_lng, lat2=entrega_lat, lng2=entrega_lng
        )
        if distancia <= radius_m:
            return LLEGO_ENTREGA
        return None

    return None


def current_payout_period(now: datetime) -> tuple[datetime, datetime]:
    """Ventana de pago semanal del repartidor: domingo 12:00pm (hora Bogota)
    hasta el siguiente domingo 12:00pm. El pago de lo acumulado en esa
    ventana se envia justo al cierre, momento en que el contador semanal
    vuelve a 0 (el historial completo nunca se reinicia)."""

    local_now = now.astimezone(PAYOUT_TIMEZONE)
    dias_desde_domingo = (local_now.weekday() + 1) % 7
    inicio = (local_now - timedelta(days=dias_desde_domingo)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    if inicio > local_now:
        inicio -= timedelta(days=7)
    fin = inicio + timedelta(days=7)
    return inicio, fin


def validate_can_mark_salio(estado_actual: str) -> None:
    if estado_actual != LLEGO_RECOGIDA:
        raise ValidationError(
            "Solo puedes marcar que saliste con el pedido despues de llegar al punto de recogida"
        )


def validate_can_mark_finalizado(estado_actual: str) -> None:
    if estado_actual != LLEGO_ENTREGA:
        raise ValidationError(
            "Solo puedes finalizar el pedido despues de llegar a la direccion de entrega"
        )
