from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class NotificacionRepository(Protocol):
    def get_by_id(self, notificacion_id: int) -> Any | None: ...

    def save_leida(self, notificacion: Any) -> None: ...

    def list_for_user(self, usuario: Any) -> Any: ...


@runtime_checkable
class PushSubscriptionRepository(Protocol):
    def create_or_update(self, *, usuario: Any, endpoint: str, p256dh: str, auth: str) -> Any: ...

    def list_for_user(self, usuario: Any) -> list[Any]: ...

    def delete_by_endpoint(self, endpoint: str) -> None: ...
