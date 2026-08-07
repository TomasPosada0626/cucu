from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PublicacionRepository(Protocol):
    def list_all(self) -> Any: ...

    def list_active_with_location(self) -> Any: ...

    def list_for_user(self, user: Any) -> Any: ...

    def get_by_id(self, publicacion_id: int) -> Any | None: ...

    def create(self, **fields: Any) -> Any: ...

    def update(self, publicacion: Any, **changes: Any) -> None: ...

    def delete(self, publicacion: Any) -> None: ...


@runtime_checkable
class PedidoRepository(Protocol):
    def get_active_for_user(self, user: Any) -> Any | None: ...

    def get_for_user(self, user: Any, pedido_id: int) -> Any | None: ...

    def get_by_id_with_relations(self, pedido_id: int) -> Any | None: ...

    def list_for_user(self, user: Any) -> Any: ...

    def mark_delivered(self, pedido: Any) -> None: ...

    def save_estado(self, pedido: Any) -> None: ...

    def create_order(
        self,
        *,
        user: Any,
        telefono: str,
        direccion_entrega: str,
        direccion_entrega_detalles: str,
        direccion_entrega_latitud: Any,
        direccion_entrega_longitud: Any,
        counts: dict[int, int],
    ) -> Any: ...


@runtime_checkable
class UbicacionRepository(Protocol):
    def create(self, **fields: Any) -> Any: ...

    def delete_if_orphan(self, ubicacion: Any) -> None: ...
