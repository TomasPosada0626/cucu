from __future__ import annotations

from .errors import NotFoundError, ValidationError
from .repositories.market_repository import PostgresMarketRepository


class MarketService:
    def __init__(self, *, repository: PostgresMarketRepository) -> None:
        self.repository = repository

    def create_publication(self, *, autor_id: int, titulo: str, descripcion: str, precio: float, direccion_texto: str):
        if int(autor_id) <= 0:
            raise ValidationError("El autor es invalido")
        titulo = str(titulo or "").strip()
        descripcion = str(descripcion or "").strip()
        direccion_texto = str(direccion_texto or "").strip()
        if not titulo:
            raise ValidationError("El titulo es obligatorio")
        if not descripcion:
            raise ValidationError("La descripcion es obligatoria")
        if not direccion_texto:
            raise ValidationError("La direccion es obligatoria")
        try:
            price = float(precio)
        except (TypeError, ValueError) as exc:
            raise ValidationError("El precio es invalido") from exc
        if price <= 0:
            raise ValidationError("El precio debe ser mayor a 0")

        return self.repository.create_publication(
            autor_id=int(autor_id),
            titulo=titulo,
            descripcion=descripcion,
            precio=price,
            direccion_texto=direccion_texto,
        )

    def list_publications(self):
        return self.repository.list_publications()

    def create_order(self, *, publicacion_id: int, comprador_id: int, cantidad: int):
        try:
            pub_id = int(publicacion_id)
            buyer_id = int(comprador_id)
            quantity = int(cantidad)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Datos de orden invalidos") from exc
        if pub_id <= 0 or buyer_id <= 0:
            raise ValidationError("Datos de orden invalidos")
        if quantity <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")

        publication = self.repository.get_publication(pub_id)
        if publication is None:
            raise NotFoundError("Publicacion no encontrada")
        total = float(publication.precio) * quantity
        return self.repository.create_order(
            publicacion_id=pub_id,
            comprador_id=buyer_id,
            cantidad=quantity,
            total=total,
            estado="pendiente",
        )

    def list_orders(self):
        return self.repository.list_orders()

    def get_order(self, *, order_id: int):
        order = self.repository.get_order(int(order_id))
        if order is None:
            raise NotFoundError("Orden no encontrada")
        return order
