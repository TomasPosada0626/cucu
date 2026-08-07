from __future__ import annotations

from dataclasses import dataclass

from common.exceptions import ValidationError

DELIVERY_FEE_COP = 5000.0


@dataclass(frozen=True)
class PublicacionSnapshot:
    id: int
    titulo: str
    estado: str
    stock: int
    maximo_por_venta: int
    precio: float


def validate_and_price_items(
    counts: dict[int, int],
    snapshots: dict[int, PublicacionSnapshot],
    *,
    delivery_fee: float = DELIVERY_FEE_COP,
) -> float:
    """Valida las reglas de negocio de un pedido (estado, stock, maximo por venta)
    y calcula el total. No toca la base de datos: recibe snapshots ya cargados."""
    total = 0.0
    for publicacion_id, qty in counts.items():
        snapshot = snapshots[publicacion_id]

        if snapshot.estado.upper() != "ACTIVA":
            raise ValidationError(f"La publicación '{snapshot.titulo}' no está disponible")

        if snapshot.stock < qty:
            raise ValidationError(
                f"Stock insuficiente para '{snapshot.titulo}'. Disponibles: {snapshot.stock}"
            )

        maximo_por_venta = max(1, snapshot.maximo_por_venta)
        if qty > maximo_por_venta:
            raise ValidationError(
                f"Solo puedes pedir hasta {maximo_por_venta} unidad"
                f"{'es' if maximo_por_venta != 1 else ''} de '{snapshot.titulo}' por compra"
            )

        total += snapshot.precio * qty

    total += delivery_fee

    if total <= 0:
        raise ValidationError("El total debe ser mayor a 0")

    return total
