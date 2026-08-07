from __future__ import annotations

from common.exceptions import ConflictError, NotFoundError

from ..infrastructure.factories import NotificacionFactory
from .repositories import NotificacionRepository


def _default_notificacion_repository() -> NotificacionRepository:
    from ..infrastructure.repositories_impl import DjangoNotificacionRepository

    return DjangoNotificacionRepository()


class NotificacionService:
    def __init__(self, *, factory=NotificacionFactory, repository: NotificacionRepository | None = None):
        self._factory = factory
        self._repository = repository or _default_notificacion_repository()

    def enviar(self, usuario, tipo, mensaje):
        return self._factory.crear(usuario=usuario, tipo=tipo, mensaje=mensaje)

    def marcar_leida(self, notificacion_id):
        notificacion = self._repository.get_by_id(notificacion_id)
        if notificacion is None:
            raise NotFoundError("Notificación no encontrada")

        if notificacion.leida:
            raise ConflictError("La notificación ya fue leída")

        notificacion.leida = True
        self._repository.save_leida(notificacion)
        return notificacion

    def obtener_usuario(self, usuario):
        return self._repository.list_for_user(usuario)
