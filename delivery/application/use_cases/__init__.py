from __future__ import annotations

from ...domain.services import DeliveryService


class SetDisponibilidadUseCase:
    def __init__(self, *, service: DeliveryService | None = None):
        self._service = service or DeliveryService()

    def execute(self, *, usuario, activo: bool):
        return self._service.set_disponibilidad(usuario=usuario, activo=activo)


class ListarPedidosCercanosUseCase:
    def __init__(self, *, service: DeliveryService | None = None):
        self._service = service or DeliveryService()

    def execute(self, *, usuario):
        return self._service.listar_pedidos_cercanos(usuario=usuario)


class AceptarPedidoUseCase:
    def __init__(self, *, service: DeliveryService | None = None):
        self._service = service or DeliveryService()

    def execute(self, *, usuario, pedido_id: int):
        return self._service.aceptar_pedido(usuario=usuario, pedido_id=pedido_id)


class ActualizarUbicacionUseCase:
    def __init__(self, *, service: DeliveryService | None = None):
        self._service = service or DeliveryService()

    def execute(self, *, usuario, latitud: float, longitud: float):
        return self._service.actualizar_ubicacion(usuario=usuario, latitud=latitud, longitud=longitud)


class AsignacionActivaUseCase:
    def __init__(self, *, service: DeliveryService | None = None):
        self._service = service or DeliveryService()

    def execute(self, *, usuario):
        return self._service.asignacion_activa(usuario=usuario)


class MarcarSalioUseCase:
    def __init__(self, *, service: DeliveryService | None = None):
        self._service = service or DeliveryService()

    def execute(self, *, usuario, pedido_id: int):
        return self._service.marcar_salio(usuario=usuario, pedido_id=pedido_id)


class MarcarFinalizadoUseCase:
    def __init__(self, *, service: DeliveryService | None = None):
        self._service = service or DeliveryService()

    def execute(self, *, usuario, pedido_id: int):
        return self._service.marcar_finalizado(usuario=usuario, pedido_id=pedido_id)


class HistorialEntregasUseCase:
    def __init__(self, *, service: DeliveryService | None = None):
        self._service = service or DeliveryService()

    def execute(self, *, usuario):
        return self._service.historial_entregas(usuario=usuario)


class ResumenRepartidorUseCase:
    def __init__(self, *, service: DeliveryService | None = None):
        self._service = service or DeliveryService()

    def execute(self, *, usuario):
        return self._service.resumen(usuario=usuario)


class EstadoParaCompradorUseCase:
    def __init__(self, *, service: DeliveryService | None = None):
        self._service = service or DeliveryService()

    def execute(self, *, usuario, pedido_id: int):
        return self._service.estado_para_comprador(usuario=usuario, pedido_id=pedido_id)
