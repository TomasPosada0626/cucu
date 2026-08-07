from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PedidoLookupRepository(Protocol):
    """Puerto de solo lectura hacia el Pedido de `market`, para que
    payments/domain no dependa directamente del ORM de otra app."""

    def get_by_id(self, pedido_id: int) -> Any | None: ...


@runtime_checkable
class PagoRepository(Protocol):
    def create(self, **fields: Any) -> Any: ...
