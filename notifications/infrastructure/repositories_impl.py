from __future__ import annotations

from .models import Notificacion, PushSubscription


class DjangoNotificacionRepository:
    def get_by_id(self, notificacion_id: int) -> Notificacion | None:
        return Notificacion.objects.filter(id=notificacion_id).first()

    def save_leida(self, notificacion: Notificacion) -> None:
        notificacion.save(update_fields=["leida"])

    def list_for_user(self, usuario):
        return Notificacion.objects.filter(usuario=usuario).order_by("-fecha_envio")


class DjangoPushSubscriptionRepository:
    def create_or_update(self, *, usuario, endpoint: str, p256dh: str, auth: str) -> PushSubscription:
        subscription, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={"usuario": usuario, "p256dh": p256dh, "auth": auth},
        )
        return subscription

    def list_for_user(self, usuario) -> list[PushSubscription]:
        return list(PushSubscription.objects.filter(usuario=usuario))

    def delete_by_endpoint(self, endpoint: str) -> None:
        PushSubscription.objects.filter(endpoint=endpoint).delete()
