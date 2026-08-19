from __future__ import annotations

from ...domain.services import AcceptOrderService, OrderService
from ...infrastructure.cache import invalidate_catalog_cache


class CreateOrderUseCase:
    def __init__(self, *, order_service: OrderService | None = None):
        self._order_service = order_service or OrderService()

    def execute(self, *, user, **payload):
        # Un pedido decrementa el stock de la publicacion - el catalogo cacheado
        # debe reflejarlo de inmediato, no esperar a que expire el TTL.
        pedido = self._order_service.create_order(user=user, **payload)
        invalidate_catalog_cache()
        return pedido


class GetOrderForUserUseCase:
    def __init__(self, *, order_service: OrderService | None = None):
        self._order_service = order_service or OrderService()

    def execute(self, *, user, pedido_id: int):
        return self._order_service.get_order_for_user(user=user, pedido_id=pedido_id)


class MarkOrderDeliveredUseCase:
    def __init__(self, *, order_service: OrderService | None = None):
        self._order_service = order_service or OrderService()

    def execute(self, *, user, pedido_id: int):
        return self._order_service.mark_order_delivered(user=user, pedido_id=pedido_id)


class SetPropinaUseCase:
    def __init__(self, *, order_service: OrderService | None = None):
        self._order_service = order_service or OrderService()

    def execute(self, *, user, pedido_id: int, propina: float):
        return self._order_service.set_propina(user=user, pedido_id=pedido_id, propina=propina)


class ListOrdersForUserUseCase:
    def __init__(self, *, order_service: OrderService | None = None):
        self._order_service = order_service or OrderService()

    def execute(self, *, user):
        return self._order_service.list_orders_for_user(user=user)


class RateOrderUseCase:
    def __init__(self, *, order_service: OrderService | None = None):
        self._order_service = order_service or OrderService()

    def execute(self, *, user, pedido_id: int, puntuacion: int, comentario: str):
        return self._order_service.rate_order(
            user=user, pedido_id=pedido_id, puntuacion=puntuacion, comentario=comentario
        )


class AcceptOrderUseCase:
    def __init__(self, *, accept_order_service: AcceptOrderService | None = None):
        self._accept_order_service = accept_order_service or AcceptOrderService()

    def execute(self, *, user, pedido_id: int):
        return self._accept_order_service.accept_order(user=user, pedido_id=pedido_id)
