from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class NotificacionRepository(Protocol):
    def get_by_id(self, notificacion_id: int) -> Any | None: ...

    def save_leida(self, notificacion: Any) -> None: ...

    def list_for_user(self, usuario: Any) -> Any: ...
