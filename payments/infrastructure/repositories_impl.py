from __future__ import annotations

from typing import Any

from .models import Pago


class DjangoPedidoLookupRepository:
    def get_by_id(self, pedido_id: int):
        from market.infrastructure.models import Pedido

        return Pedido.objects.filter(id=pedido_id).first()


class DjangoPagoRepository:
    def create(self, **fields: Any) -> Pago:
        return Pago.objects.create(**fields)
