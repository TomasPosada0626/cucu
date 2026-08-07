from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from common.exceptions import ValidationError

from .repositories import PedidoRepository


@dataclass
class PedidoBuilder:
    pedido_repository: PedidoRepository = field(default=None)  # type: ignore[assignment]
    user = None
    telefono: str | None = None
    direccion_entrega: str | None = None
    direccion_entrega_detalles: str | None = None
    direccion_entrega_latitud: Decimal | None = None
    direccion_entrega_longitud: Decimal | None = None
    publicacion_id: int | None = None
    publicacion_ids: list[int] | None = None

    def __post_init__(self) -> None:
        if self.pedido_repository is None:
            from ..infrastructure.repositories_impl import DjangoPedidoRepository

            self.pedido_repository = DjangoPedidoRepository()

    def for_user(self, user):
        self.user = user
        return self

    def with_telefono(self, telefono: str):
        self.telefono = telefono
        return self

    def with_delivery_address(self, direccion_entrega: str, direccion_entrega_detalles: str | None = None):
        self.direccion_entrega = direccion_entrega
        self.direccion_entrega_detalles = direccion_entrega_detalles
        return self

    def with_delivery_coordinates(self, latitud: Decimal | None, longitud: Decimal | None):
        self.direccion_entrega_latitud = latitud
        self.direccion_entrega_longitud = longitud
        return self

    def with_publicacion_id(self, publicacion_id: int | None):
        self.publicacion_id = publicacion_id
        return self

    def with_publicacion_ids(self, publicacion_ids: list[int] | None):
        self.publicacion_ids = publicacion_ids
        return self

    def build(self):
        if self.user is None:
            raise ValueError("user es requerido")

        telefono = (self.telefono or "").strip()
        if not telefono:
            raise ValidationError("El teléfono es requerido")

        direccion_entrega = (self.direccion_entrega or "").strip()
        if not direccion_entrega:
            raise ValidationError("La dirección de entrega es requerida")

        direccion_entrega_detalles = (self.direccion_entrega_detalles or "").strip()

        has_one = self.publicacion_id is not None
        has_many = self.publicacion_ids is not None
        if has_one and has_many:
            raise ValidationError("Usa publicacion_id o publicacion_ids (no ambos)")

        publicacion_ids: list[int]
        if self.publicacion_ids is None:
            publicacion_ids = []
        else:
            publicacion_ids = list(self.publicacion_ids)

        if self.publicacion_id is not None:
            publicacion_ids = [int(self.publicacion_id)]

        if not publicacion_ids:
            raise ValidationError("Debes seleccionar al menos una publicación")

        counts: dict[int, int] = {}
        for pid in publicacion_ids:
            pid_int = int(pid)
            counts[pid_int] = counts.get(pid_int, 0) + 1

        return self.pedido_repository.create_order(
            user=self.user,
            telefono=telefono,
            direccion_entrega=direccion_entrega,
            direccion_entrega_detalles=direccion_entrega_detalles,
            direccion_entrega_latitud=self.direccion_entrega_latitud,
            direccion_entrega_longitud=self.direccion_entrega_longitud,
            counts=counts,
        )
