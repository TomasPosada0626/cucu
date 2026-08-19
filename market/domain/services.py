from __future__ import annotations

from math import asin, cos, radians, sin
from typing import Callable

from common.domain.ports import RatingServicePort
from common.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from geo.domain.services import GeocodingService
from notifications.domain.services import NotificacionService

from .builders import PedidoBuilder
from .repositories import PedidoRepository, PublicacionRepository, UbicacionRepository


def _default_publicacion_repository() -> PublicacionRepository:
    from ..infrastructure.repositories_impl import DjangoPublicacionRepository

    return DjangoPublicacionRepository()


def _default_pedido_repository() -> PedidoRepository:
    from ..infrastructure.repositories_impl import DjangoPedidoRepository

    return DjangoPedidoRepository()


def _default_ubicacion_repository() -> UbicacionRepository:
    from ..infrastructure.repositories_impl import DjangoUbicacionRepository

    return DjangoUbicacionRepository()


def _default_rating_service() -> RatingServicePort:
    from common.infrastructure.adapters import HttpSupportServiceAdapter

    return HttpSupportServiceAdapter()


class AcceptOrderService:
    def __init__(
        self,
        *,
        pedido_repository: PedidoRepository | None = None,
        notificacion_service: NotificacionService | None = None,
    ):
        self._pedido_repository = pedido_repository or _default_pedido_repository()
        self._notificacion_service = notificacion_service or NotificacionService()

    def accept_order(self, *, user, pedido_id: int):
        # El pedido lo acepta el vendedor (dueno de la publicacion), no el
        # comprador, asi que se busca por id sin filtrar por usuario dueno.
        pedido = self._pedido_repository.get_by_id_with_relations(pedido_id)
        if pedido is None:
            raise NotFoundError("Pedido no encontrado")

        if pedido.publicacion.usuario_id != user.id:
            raise PermissionDeniedError("Solo el dueño de la publicación puede aceptar el pedido")

        if pedido.estado != "PENDIENTE":
            raise ValidationError("Solo se pueden aceptar pedidos en estado PENDIENTE")

        pedido.estado = "ACEPTADO"
        self._pedido_repository.save_estado(pedido)

        self._notificacion_service.enviar(
            usuario=pedido.usuario,
            tipo="pedido",
            mensaje=f"Tu pedido #{pedido.id} de '{pedido.publicacion.titulo}' fue aceptado",
        )

        return pedido


class CatalogService:
    def __init__(
        self,
        *,
        publicacion_repository: PublicacionRepository | None = None,
        ubicacion_repository: UbicacionRepository | None = None,
        geocoding_service: GeocodingService | None = None,
    ):
        self._publicacion_repository = publicacion_repository or _default_publicacion_repository()
        self._ubicacion_repository = ubicacion_repository or _default_ubicacion_repository()
        self._geocoding_service = geocoding_service or GeocodingService()

    def list_publicaciones(self):
        return self._publicacion_repository.list_all()

    def list_publicaciones_cercanas(
        self,
        *,
        latitud: float | None = None,
        longitud: float | None = None,
        direccion_texto: str | None = None,
        radio_km: float = 5.0,
    ):
        radio_limitado = min(float(radio_km), 5.0)
        latitud_resuelta, longitud_resuelta = self._resolve_coordinates(
            latitud=latitud,
            longitud=longitud,
            direccion_texto=direccion_texto,
        )
        publicaciones = self._publicacion_repository.list_active_with_location()

        cercanas = []
        for publicacion in publicaciones:
            ubicacion = publicacion.ubicacion
            if ubicacion is None:
                continue

            distancia_km = self._haversine_km(
                latitud_1=float(latitud_resuelta),
                longitud_1=float(longitud_resuelta),
                latitud_2=float(ubicacion.latitud),
                longitud_2=float(ubicacion.longitud),
            )
            if distancia_km <= radio_limitado:
                publicacion.distancia_km = distancia_km
                cercanas.append(publicacion)

        cercanas.sort(key=lambda publicacion: publicacion.distancia_km)
        return cercanas

    def create_publicacion(
        self,
        *,
        user,
        titulo: str,
        descripcion: str,
        categoria: str | None = None,
        ingredientes: list[str] | None = None,
        imagen=None,
        stock: int | None = None,
        maximo_por_venta: int | None = None,
        precio: float,
        direccion_texto: str,
        latitud=None,
        longitud=None,
    ):
        latitud_resuelta, longitud_resuelta, direccion_resuelta = self._resolve_location_for_publicacion(
            direccion_texto=direccion_texto,
            latitud=latitud,
            longitud=longitud,
        )
        ubicacion = self._ubicacion_repository.create(
            direccion_texto=direccion_resuelta,
            latitud=latitud_resuelta,
            longitud=longitud_resuelta,
        )
        return self._publicacion_repository.create(
            titulo=titulo.strip(),
            descripcion=descripcion.strip(),
            categoria=self._clean_categoria(categoria),
            ingredientes=self._clean_ingredientes(ingredientes),
            imagen=imagen,
            imagen_thumb=getattr(imagen, "imagen_thumb_content", None),
            stock=int(stock if stock is not None else 10),
            maximo_por_venta=max(1, int(maximo_por_venta if maximo_por_venta is not None else 5)),
            precio=float(precio),
            usuario=user,
            ubicacion=ubicacion,
        )

    def list_publicaciones_for_user(self, *, user):
        return self._publicacion_repository.list_for_user(user)

    def update_publicacion(self, *, user, publicacion_id: int, **changes):
        publicacion = self._publicacion_repository.get_by_id(publicacion_id)
        if publicacion is None:
            raise NotFoundError("Publicación no encontrada")

        if publicacion.usuario_id != user.id:
            raise PermissionDeniedError("Solo puedes actualizar tus propias publicaciones")

        clean_changes: dict = {}

        if "titulo" in changes:
            titulo = str(changes["titulo"] or "").strip()
            if not titulo:
                raise ValidationError("El título es requerido")
            clean_changes["titulo"] = titulo

        if "descripcion" in changes:
            descripcion = str(changes["descripcion"] or "").strip()
            if not descripcion:
                raise ValidationError("La descripción es requerida")
            clean_changes["descripcion"] = descripcion

        if "categoria" in changes:
            clean_changes["categoria"] = self._clean_categoria(changes.get("categoria"))

        if "ingredientes" in changes:
            clean_changes["ingredientes"] = self._clean_ingredientes(changes.get("ingredientes"))

        if "stock" in changes:
            clean_changes["stock"] = max(0, int(changes.get("stock") or 0))

        if "maximo_por_venta" in changes:
            clean_changes["maximo_por_venta"] = max(1, int(changes.get("maximo_por_venta") or 1))

        if "precio" in changes:
            precio = float(changes.get("precio") or 0)
            if precio <= 0:
                raise ValidationError("El precio debe ser mayor a 0")
            clean_changes["precio"] = precio

        if "estado" in changes:
            clean_changes["estado"] = str(changes.get("estado") or "ACTIVA").strip().upper()

        if not clean_changes:
            raise ValidationError("No hay cambios para guardar")

        self._publicacion_repository.update(publicacion, **clean_changes)
        return publicacion

    def delete_publicacion(self, *, user, publicacion_id: int) -> None:
        publicacion = self._publicacion_repository.get_by_id(publicacion_id)
        if publicacion is None:
            raise NotFoundError("Publicación no encontrada")

        if publicacion.usuario_id != user.id:
            raise PermissionDeniedError("Solo puedes eliminar tus propias publicaciones")

        ubicacion = publicacion.ubicacion
        self._publicacion_repository.delete(publicacion)
        self._ubicacion_repository.delete_if_orphan(ubicacion)

    @staticmethod
    def _clean_ingredientes(ingredientes: list[str] | None) -> list[str]:
        out: list[str] = []
        for item in ingredientes or []:
            text = str(item or "").strip()
            if not text:
                continue
            if text in out:
                continue
            out.append(text)
        return out

    @staticmethod
    def _clean_categoria(categoria: str | None) -> str:
        allowed = {"mexicana", "italiana", "sana", "postres", "otra"}
        value = str(categoria or "").strip().lower()
        if not value:
            return ""
        if value not in allowed:
            raise ValidationError("La categoría enviada no es válida")
        return value

    def _resolve_location_for_publicacion(self, *, direccion_texto: str, latitud=None, longitud=None):
        if latitud is not None and longitud is not None:
            return latitud, longitud, direccion_texto.strip()

        geocoded = self._geocoding_service.geocode_address(direccion_texto=direccion_texto)
        return geocoded.latitud, geocoded.longitud, geocoded.direccion_texto

    def _resolve_coordinates(self, *, latitud=None, longitud=None, direccion_texto: str | None = None):
        if latitud is not None and longitud is not None:
            return latitud, longitud
        if not direccion_texto:
            raise ValidationError("Debes enviar tu ubicación o una dirección")

        geocoded = self._geocoding_service.geocode_address(direccion_texto=direccion_texto)
        return geocoded.latitud, geocoded.longitud

    @staticmethod
    def _haversine_km(*, latitud_1: float, longitud_1: float, latitud_2: float, longitud_2: float) -> float:
        radio_tierra_km = 6371.0
        delta_latitud = radians(latitud_2 - latitud_1)
        delta_longitud = radians(longitud_2 - longitud_1)
        origen_latitud = radians(latitud_1)
        destino_latitud = radians(latitud_2)

        a = (
            sin(delta_latitud / 2) ** 2
            + cos(origen_latitud) * cos(destino_latitud) * sin(delta_longitud / 2) ** 2
        )
        return 2 * radio_tierra_km * asin(a**0.5)


class OrderService:
    def __init__(
        self,
        *,
        pedido_repository: PedidoRepository | None = None,
        pedido_builder_factory: Callable[[], PedidoBuilder] | None = None,
        notificacion_service: NotificacionService | None = None,
        rating_service: RatingServicePort | None = None,
    ):
        self._pedido_repository = pedido_repository or _default_pedido_repository()
        self._pedido_builder_factory = pedido_builder_factory or (
            lambda: PedidoBuilder(pedido_repository=self._pedido_repository)
        )
        self._notificacion_service = notificacion_service or NotificacionService()
        self._rating_service = rating_service or _default_rating_service()

    def create_order(
        self,
        *,
        user,
        telefono: str,
        direccion_entrega: str,
        direccion_entrega_detalles: str = "",
        direccion_entrega_latitud=None,
        direccion_entrega_longitud=None,
        publicacion_id: int | None = None,
        publicacion_ids: list[int] | None = None,
        total: float | None = None,
    ):
        _ = total

        active_order = self._pedido_repository.get_active_for_user(user)
        if active_order is not None:
            raise ValidationError(
                f"Ya tienes un pedido activo (#{active_order.id}). Debes esperar a que sea entregado para crear otro."
            )

        latitud_resuelta, longitud_resuelta = self._resolve_delivery_coordinates(
            direccion_entrega=direccion_entrega,
            direccion_entrega_latitud=direccion_entrega_latitud,
            direccion_entrega_longitud=direccion_entrega_longitud,
        )

        pedido_builder = self._pedido_builder_factory()
        pedido = (
            pedido_builder.for_user(user)
            .with_telefono(telefono)
            .with_delivery_address(direccion_entrega, direccion_entrega_detalles)
            .with_delivery_coordinates(latitud_resuelta, longitud_resuelta)
            .with_publicacion_id(publicacion_id)
            .with_publicacion_ids(publicacion_ids)
            .build()
        )

        self._notificacion_service.enviar(
            usuario=pedido.publicacion.usuario,
            tipo="pedido",
            mensaje=f"Tienes un nuevo pedido #{pedido.id} de '{pedido.publicacion.titulo}'",
        )

        return pedido

    def get_order_for_user(self, *, user, pedido_id: int):
        pedido = self._pedido_repository.get_for_user(user, pedido_id)
        if pedido is None:
            raise NotFoundError("Pedido no encontrado")
        return pedido

    def mark_order_delivered(self, *, user, pedido_id: int):
        pedido = self._pedido_repository.get_for_user(user, pedido_id)
        if pedido is None:
            raise NotFoundError("Pedido no encontrado")

        if pedido.estado == "ENTREGADO":
            return pedido

        self._pedido_repository.mark_delivered(pedido)

        self._notificacion_service.enviar(
            usuario=pedido.publicacion.usuario,
            tipo="pedido",
            mensaje=f"El pedido #{pedido.id} de '{pedido.publicacion.titulo}' fue marcado como entregado",
        )

        return pedido

    def set_propina(self, *, user, pedido_id: int, propina: float):
        pedido = self._pedido_repository.get_for_user(user, pedido_id)
        if pedido is None:
            raise NotFoundError("Pedido no encontrado")

        self._pedido_repository.set_propina(pedido, propina)
        return pedido

    def list_orders_for_user(self, *, user):
        return self._pedido_repository.list_for_user(user)

    def rate_order(self, *, user, pedido_id: int, puntuacion: int, comentario: str):
        pedido = self._pedido_repository.get_for_user(user, pedido_id)
        if pedido is None:
            raise NotFoundError("Pedido no encontrado")

        if pedido.estado != "ENTREGADO":
            raise ValidationError("Solo se puede calificar un pedido ya entregado")
        if pedido.calificado:
            raise ValidationError("Ya calificaste este pedido")

        puntuacion_int = int(puntuacion)
        if puntuacion_int < 1 or puntuacion_int > 5:
            raise ValidationError("La puntuación debe estar entre 1 y 5")
        comentario_normalizado = str(comentario or "").strip()
        if not comentario_normalizado:
            raise ValidationError("El comentario es obligatorio")

        vendedor = pedido.publicacion.usuario

        # Si esto falla (support-service caido), la excepcion sube tal cual -
        # a diferencia del resto del flujo de pedidos, calificar no es una
        # accion critica del checkout, asi que preferimos un error claro al
        # comprador antes que marcar calificado=True sobre una calificacion
        # que en realidad nunca se guardo.
        self._rating_service.create_rating(
            usuario_id=vendedor.id,
            autor_id=user.id,
            puntuacion=puntuacion_int,
            comentario=comentario_normalizado,
        )

        self._pedido_repository.mark_calificado(pedido)
        self._refresh_reputacion(vendedor)

        self._notificacion_service.enviar(
            usuario=vendedor,
            tipo="pedido",
            mensaje=f"{user.nombre or user.email} calificó tu pedido #{pedido.id} con {puntuacion_int} estrellas",
        )

        return pedido

    def _refresh_reputacion(self, vendedor) -> None:
        # Lectura best-effort: si support-service no responde ahora mismo,
        # la calificacion que se acaba de guardar no se pierde (ya se
        # confirmo arriba) - el promedio mostrado solo queda un paso atras
        # hasta la proxima calificacion o consulta exitosa.
        ratings = self._rating_service.list_ratings(usuario_id=vendedor.id)
        if not ratings:
            return
        promedio = sum(float(r.get("puntuacion", 0)) for r in ratings) / len(ratings)
        vendedor.reputacion_promedio = round(promedio, 1)
        vendedor.total_calificaciones = len(ratings)
        vendedor.save(update_fields=["reputacion_promedio", "total_calificaciones"])

    def _resolve_delivery_coordinates(
        self,
        *,
        direccion_entrega: str,
        direccion_entrega_latitud,
        direccion_entrega_longitud,
    ):
        if direccion_entrega_latitud is not None and direccion_entrega_longitud is not None:
            return direccion_entrega_latitud, direccion_entrega_longitud

        geocoded = GeocodingService().geocode_address(direccion_texto=direccion_entrega)
        return geocoded.latitud, geocoded.longitud
