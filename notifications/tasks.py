from __future__ import annotations

from celery import shared_task
from django.utils.translation import gettext as _

from .infrastructure.models import Notificacion


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def enqueue_payment_notification(self, *, usuario_id: int, pago_id: int, pedido_id: int, estado: str):
    estado_normalizado = str(estado or "PENDIENTE").upper()
    if estado_normalizado == "AUTORIZADO":
        mensaje = _("Tu pago fue autorizado para el pedido #%(pedido_id)s") % {"pedido_id": pedido_id}
    elif estado_normalizado == "FALLIDO":
        mensaje = _("Tu pago fallo para el pedido #%(pedido_id)s") % {"pedido_id": pedido_id}
    else:
        mensaje = _("Tu pago cambio de estado a %(estado)s para el pedido #%(pedido_id)s") % {
            "estado": estado_normalizado,
            "pedido_id": pedido_id,
        }

    Notificacion.objects.create(
        tipo="pago",
        mensaje=mensaje,
        usuario_id=usuario_id,
    )

    return {
        "ok": True,
        "pago_id": pago_id,
        "pedido_id": pedido_id,
        "usuario_id": usuario_id,
        "estado": estado_normalizado,
    }
