from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RepartidorRepository(Protocol):
    def get_or_create_perfil(self, usuario: Any) -> Any: ...

    def set_activo(self, perfil: Any, activo: bool) -> None: ...

    def update_ubicacion(self, perfil: Any, *, latitud: float, longitud: float) -> None: ...


@runtime_checkable
class AsignacionRepository(Protocol):
    def get_active_for_repartidor(self, usuario: Any) -> Any | None: ...

    def get_by_pedido_id(self, pedido_id: int) -> Any | None: ...

    def create(self, *, pedido: Any, repartidor: Any) -> Any: ...

    def mark_llego_recogida(self, asignacion: Any) -> None: ...

    def mark_salio(self, asignacion: Any) -> None: ...

    def mark_llego_entrega(self, asignacion: Any, *, distancia_metros: float = 0.0) -> None: ...

    def mark_finalizado(self, asignacion: Any) -> None: ...

    def list_historial(self, usuario: Any) -> list[Any]: ...


@runtime_checkable
class PedidoDeliveryRepository(Protocol):
    def list_pending_near(
        self,
        *,
        latitud: float,
        longitud: float,
        radius_km: float,
        excluded_pedido_ids: set[int] | None = None,
    ) -> list[Any]: ...

    def get_by_id(self, pedido_id: int) -> Any | None: ...

    def mark_entregado(self, pedido: Any) -> None: ...


@runtime_checkable
class PedidoRechazoRepository(Protocol):
    def registrar(self, *, pedido_id: int, repartidor: Any) -> None: ...

    def ids_rechazados_por(self, repartidor: Any) -> set[int]: ...
