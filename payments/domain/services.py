from __future__ import annotations

import logging

from django.utils import timezone

from common.exceptions import NotFoundError, ValidationError
from transactions.domain.builders import ensure_transaccion_for_pedido

from ..infrastructure.gateways import PaymentGatewayFactory
from .repositories import PagoRepository, PedidoLookupRepository

logger = logging.getLogger(__name__)


def _default_pedido_lookup_repository() -> PedidoLookupRepository:
    from ..infrastructure.repositories_impl import DjangoPedidoLookupRepository

    return DjangoPedidoLookupRepository()


def _default_pago_repository() -> PagoRepository:
    from ..infrastructure.repositories_impl import DjangoPagoRepository

    return DjangoPagoRepository()


class PaymentService:
    def __init__(
        self,
        *,
        gateway_factory=PaymentGatewayFactory,
        ensure_transaccion_func=ensure_transaccion_for_pedido,
        pedido_lookup_repository: PedidoLookupRepository | None = None,
        pago_repository: PagoRepository | None = None,
    ):
        self._gateway_factory = gateway_factory
        self._ensure_transaccion = ensure_transaccion_func
        self._pedido_lookup_repository = pedido_lookup_repository or _default_pedido_lookup_repository()
        self._pago_repository = pago_repository or _default_pago_repository()

    def register_payment(self, *, user, pedido_id: int, metodo: str, monto: float | None = None):
        pedido = self._pedido_lookup_repository.get_by_id(pedido_id)
        if pedido is None:
            raise NotFoundError("Pedido no encontrado")

        if pedido.usuario_id != user.id:
            raise ValidationError("No puedes pagar un pedido que no es tuyo")

        expected_monto = float(pedido.total)
        if expected_monto <= 0:
            raise ValidationError("El total del pedido debe ser mayor a 0")

        if monto is None:
            monto_to_charge = expected_monto
        else:
            provided = float(monto)
            if abs(provided - expected_monto) > 0.01:
                raise ValidationError("El monto no coincide con el total del pedido")
            monto_to_charge = expected_monto

        gateway = self._gateway_factory.get_gateway(method=metodo)
        authorized = gateway.authorize(amount=float(monto_to_charge))

        pago = self._pago_repository.create(
            pedido=pedido,
            metodo=metodo,
            monto=monto_to_charge,
            estado="AUTORIZADO" if authorized else "FALLIDO",
            fecha_autorizacion=timezone.now() if authorized else None,
        )

        if authorized:
            self._ensure_transaccion(pedido)

        try:
            from notifications.tasks import enqueue_payment_notification

            enqueue_payment_notification.delay(
                usuario_id=user.id,
                pago_id=pago.id,
                pedido_id=pedido.id,
                estado=pago.estado,
            )
        except Exception:
            logger.exception("No se pudo encolar la notificacion asincrona del pago", extra={"pago_id": pago.id})

        return pago
