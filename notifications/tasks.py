from __future__ import annotations

from celery import shared_task
from django.utils.translation import gettext as _

from accounts.infrastructure.models import User

from .domain.services import NotificacionService


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

    usuario = User.objects.get(id=usuario_id)
    NotificacionService().enviar(usuario, "pago", mensaje)

    return {
        "ok": True,
        "pago_id": pago_id,
        "pedido_id": pedido_id,
        "usuario_id": usuario_id,
        "estado": estado_normalizado,
    }


@shared_task(bind=True)
def trigger_report_generation(self, *, requester_email: str):
    import time
    # Simula trabajo pesado asíncrono
    time.sleep(2)
    return {
        "status": "completed",
        "report_type": "summary_report",
        "requested_by": requester_email
    }
