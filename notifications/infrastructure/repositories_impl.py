from __future__ import annotations

from .models import Notificacion


class DjangoNotificacionRepository:
    def get_by_id(self, notificacion_id: int) -> Notificacion | None:
        return Notificacion.objects.filter(id=notificacion_id).first()

    def save_leida(self, notificacion: Notificacion) -> None:
        notificacion.save(update_fields=["leida"])

    def list_for_user(self, usuario):
        return Notificacion.objects.filter(usuario=usuario).order_by("-fecha_envio")
