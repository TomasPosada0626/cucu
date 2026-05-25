from __future__ import annotations

from .errors import ConflictError, NotFoundError, ValidationError
from .repositories.notification_repository import SQLiteNotificationRepository


class NotificationService:
    ALLOWED_TYPES = {"pedido", "pago", "cerca", "sistema"}

    def __init__(self, *, repository: SQLiteNotificationRepository) -> None:
        self.repository = repository

    def create_notification(self, *, usuario_id: int, tipo: str, mensaje: str):
        if int(usuario_id) <= 0:
            raise ValidationError("El usuario es invalido")
        normalized_type = str(tipo or "").strip().lower()
        if normalized_type not in self.ALLOWED_TYPES:
            raise ValidationError("Tipo de notificacion no valido")
        normalized_message = str(mensaje or "").strip()
        if not normalized_message:
            raise ValidationError("El mensaje es obligatorio")
        return self.repository.create(usuario_id=int(usuario_id), tipo=normalized_type, mensaje=normalized_message)

    def get_user_notifications(self, *, usuario_id: int):
        if int(usuario_id) <= 0:
            raise ValidationError("El usuario es invalido")
        return self.repository.list_by_user(usuario_id=int(usuario_id))

    def mark_as_read(self, *, notification_id: int):
        notification = self.repository.get_by_id(int(notification_id))
        if notification is None:
            raise NotFoundError("Notificacion no encontrada")
        if notification.leida:
            raise ConflictError("La notificacion ya fue leida")
        updated = self.repository.mark_as_read(int(notification_id))
        if updated is None:
            raise NotFoundError("Notificacion no encontrada")
        return updated
