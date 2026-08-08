from __future__ import annotations

from common.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from notifications.domain.services import NotificacionService

from .repositories import AsignacionRepository, PedidoDeliveryRepository, RepartidorRepository
from .rules import LLEGO_ENTREGA, LLEGO_RECOGIDA, next_state_after_location_update, validate_can_mark_finalizado, validate_can_mark_salio


def _default_repartidor_repo() -> RepartidorRepository:
    from ..infrastructure.repositories_impl import DjangoRepartidorRepository

    return DjangoRepartidorRepository()


def _default_asignacion_repo() -> AsignacionRepository:
    from ..infrastructure.repositories_impl import DjangoAsignacionRepository

    return DjangoAsignacionRepository()


def _default_pedido_repo() -> PedidoDeliveryRepository:
    from ..infrastructure.repositories_impl import DjangoPedidoDeliveryRepository

    return DjangoPedidoDeliveryRepository()


class DeliveryService:
    def __init__(
        self,
        *,
        repartidor_repo: RepartidorRepository | None = None,
        asignacion_repo: AsignacionRepository | None = None,
        pedido_repo: PedidoDeliveryRepository | None = None,
        notificacion_service: NotificacionService | None = None,
    ):
        self._repartidor_repo = repartidor_repo or _default_repartidor_repo()
        self._asignacion_repo = asignacion_repo or _default_asignacion_repo()
        self._pedido_repo = pedido_repo or _default_pedido_repo()
        self._notificacion_service = notificacion_service or NotificacionService()

    def set_disponibilidad(self, *, usuario, activo: bool):
        perfil = self._repartidor_repo.get_or_create_perfil(usuario)
        self._repartidor_repo.set_activo(perfil, activo)
        return perfil

    def listar_pedidos_cercanos(self, *, usuario):
        perfil = self._repartidor_repo.get_or_create_perfil(usuario)
        if perfil.latitud is None or perfil.longitud is None:
            raise ValidationError("Necesitamos tu ubicación para mostrarte pedidos cercanos")
        return self._pedido_repo.list_pending_near(
            latitud=float(perfil.latitud), longitud=float(perfil.longitud), radius_km=8.0
        )

    def aceptar_pedido(self, *, usuario, pedido_id: int):
        existing_active = self._asignacion_repo.get_active_for_repartidor(usuario)
        if existing_active is not None:
            raise ValidationError("Ya tienes un pedido activo, finalízalo antes de aceptar otro")

        pedido = self._pedido_repo.get_by_id(pedido_id)
        if pedido is None:
            raise NotFoundError("Pedido no encontrado")
        if pedido.estado != "ACEPTADO":
            raise ValidationError("Este pedido no está listo para recoger todavía")

        if self._asignacion_repo.get_by_pedido_id(pedido_id) is not None:
            raise ConflictError("Otro repartidor ya aceptó este pedido")

        asignacion = self._asignacion_repo.create(pedido=pedido, repartidor=usuario)

        self._notificacion_service.enviar(
            usuario=pedido.usuario,
            tipo="pedido",
            mensaje=f"Un repartidor va camino al restaurante por tu pedido #{pedido.id}",
        )
        return asignacion

    def actualizar_ubicacion(self, *, usuario, latitud: float, longitud: float):
        perfil = self._repartidor_repo.get_or_create_perfil(usuario)
        self._repartidor_repo.update_ubicacion(perfil, latitud=latitud, longitud=longitud)

        asignacion = self._asignacion_repo.get_active_for_repartidor(usuario)
        if asignacion is None:
            return {"asignacion": None}

        pedido = asignacion.pedido
        recogida = pedido.publicacion.ubicacion
        if recogida is None or pedido.direccion_entrega_latitud is None or pedido.direccion_entrega_longitud is None:
            return {"asignacion": asignacion}

        nuevo_estado = next_state_after_location_update(
            estado_actual=asignacion.estado,
            repartidor_lat=latitud,
            repartidor_lng=longitud,
            recogida_lat=float(recogida.latitud),
            recogida_lng=float(recogida.longitud),
            entrega_lat=float(pedido.direccion_entrega_latitud),
            entrega_lng=float(pedido.direccion_entrega_longitud),
        )

        if nuevo_estado == LLEGO_RECOGIDA:
            self._asignacion_repo.mark_llego_recogida(asignacion)
            self._notificacion_service.enviar(
                usuario=pedido.usuario,
                tipo="pedido",
                mensaje=f"El repartidor llegó al restaurante por tu pedido #{pedido.id}",
            )
        elif nuevo_estado == LLEGO_ENTREGA:
            self._asignacion_repo.mark_llego_entrega(asignacion)
            self._notificacion_service.enviar(
                usuario=pedido.usuario,
                tipo="pedido",
                mensaje=f"El repartidor llegó a tu dirección con el pedido #{pedido.id}",
            )

        return {"asignacion": asignacion}

    def asignacion_activa(self, *, usuario):
        return self._asignacion_repo.get_active_for_repartidor(usuario)

    def marcar_salio(self, *, usuario, pedido_id: int):
        asignacion = self._require_own_asignacion(usuario, pedido_id)
        validate_can_mark_salio(asignacion.estado)
        self._asignacion_repo.mark_salio(asignacion)
        self._notificacion_service.enviar(
            usuario=asignacion.pedido.usuario,
            tipo="pedido",
            mensaje=f"El repartidor salió con tu pedido #{asignacion.pedido.id}",
        )
        return asignacion

    def marcar_finalizado(self, *, usuario, pedido_id: int):
        asignacion = self._require_own_asignacion(usuario, pedido_id)
        validate_can_mark_finalizado(asignacion.estado)
        self._asignacion_repo.mark_finalizado(asignacion)
        self._pedido_repo.mark_entregado(asignacion.pedido)
        self._notificacion_service.enviar(
            usuario=asignacion.pedido.usuario,
            tipo="pedido",
            mensaje=f"Tu pedido #{asignacion.pedido.id} fue entregado. ¡Buen provecho!",
        )
        return asignacion

    def estado_para_comprador(self, *, usuario, pedido_id: int):
        pedido = self._pedido_repo.get_by_id(pedido_id)
        if pedido is None or pedido.usuario_id != usuario.id:
            raise NotFoundError("Pedido no encontrado")

        asignacion = self._asignacion_repo.get_by_pedido_id(pedido_id)
        if asignacion is None:
            return {"estado_entrega": None, "repartidor": None, "ubicacion": None}

        perfil = self._repartidor_repo.get_or_create_perfil(asignacion.repartidor)
        ubicacion = None
        if perfil.latitud is not None and perfil.longitud is not None:
            ubicacion = {"latitud": float(perfil.latitud), "longitud": float(perfil.longitud)}

        return {
            "estado_entrega": asignacion.estado,
            "repartidor": asignacion.repartidor.nombre,
            "ubicacion": ubicacion,
        }

    def _require_own_asignacion(self, usuario, pedido_id: int):
        asignacion = self._asignacion_repo.get_by_pedido_id(pedido_id)
        if asignacion is None:
            raise NotFoundError("No hay una asignación para este pedido")
        if asignacion.repartidor_id != usuario.id:
            raise PermissionDeniedError("Este pedido no está asignado a ti")
        return asignacion
