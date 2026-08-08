from __future__ import annotations

from django.utils import timezone

from ..domain.rules import haversine_meters
from .models import Asignacion, RepartidorPerfil


class DjangoRepartidorRepository:
    def get_or_create_perfil(self, usuario) -> RepartidorPerfil:
        perfil, _ = RepartidorPerfil.objects.get_or_create(usuario=usuario)
        return perfil

    def set_activo(self, perfil: RepartidorPerfil, activo: bool) -> None:
        perfil.activo = activo
        perfil.save(update_fields=["activo"])

    def update_ubicacion(self, perfil: RepartidorPerfil, *, latitud: float, longitud: float) -> None:
        perfil.latitud = latitud
        perfil.longitud = longitud
        perfil.save(update_fields=["latitud", "longitud", "actualizado_en"])


class DjangoAsignacionRepository:
    def get_active_for_repartidor(self, usuario) -> Asignacion | None:
        return (
            Asignacion.objects.select_related("pedido", "pedido__publicacion", "pedido__publicacion__ubicacion", "pedido__usuario")
            .filter(repartidor=usuario)
            .exclude(estado=Asignacion.FINALIZADO)
            .first()
        )

    def get_by_pedido_id(self, pedido_id: int) -> Asignacion | None:
        return (
            Asignacion.objects.select_related("pedido", "pedido__publicacion", "pedido__publicacion__ubicacion", "pedido__usuario", "repartidor")
            .filter(pedido_id=pedido_id)
            .first()
        )

    def create(self, *, pedido, repartidor) -> Asignacion:
        return Asignacion.objects.create(pedido=pedido, repartidor=repartidor, estado=Asignacion.ASIGNADO)

    def mark_llego_recogida(self, asignacion: Asignacion) -> None:
        asignacion.estado = Asignacion.LLEGO_RECOGIDA
        asignacion.llego_recogida_en = timezone.now()
        asignacion.save(update_fields=["estado", "llego_recogida_en"])

    def mark_salio(self, asignacion: Asignacion) -> None:
        asignacion.estado = Asignacion.EN_CAMINO_ENTREGA
        asignacion.salio_en = timezone.now()
        asignacion.save(update_fields=["estado", "salio_en"])

    def mark_llego_entrega(self, asignacion: Asignacion) -> None:
        asignacion.estado = Asignacion.LLEGO_ENTREGA
        asignacion.llego_entrega_en = timezone.now()
        asignacion.save(update_fields=["estado", "llego_entrega_en"])

    def mark_finalizado(self, asignacion: Asignacion) -> None:
        asignacion.estado = Asignacion.FINALIZADO
        asignacion.finalizado_en = timezone.now()
        asignacion.save(update_fields=["estado", "finalizado_en"])


class DjangoPedidoDeliveryRepository:
    def list_pending_near(self, *, latitud: float, longitud: float, radius_km: float) -> list:
        from market.infrastructure.models import Pedido

        candidatos = (
            Pedido.objects.select_related("publicacion", "publicacion__ubicacion", "usuario")
            .filter(estado="ACEPTADO", asignacion__isnull=True)
        )

        cercanos = []
        for pedido in candidatos:
            ubicacion = pedido.publicacion.ubicacion
            if ubicacion is None:
                continue
            distancia_km = haversine_meters(
                lat1=latitud,
                lng1=longitud,
                lat2=float(ubicacion.latitud),
                lng2=float(ubicacion.longitud),
            ) / 1000.0
            if distancia_km <= radius_km:
                pedido.distancia_km = distancia_km
                cercanos.append(pedido)

        cercanos.sort(key=lambda p: p.distancia_km)
        return cercanos

    def get_by_id(self, pedido_id: int):
        from market.infrastructure.models import Pedido

        return (
            Pedido.objects.select_related("publicacion", "publicacion__ubicacion", "usuario")
            .filter(id=pedido_id)
            .first()
        )

    def mark_entregado(self, pedido) -> None:
        pedido.estado = "ENTREGADO"
        pedido.save(update_fields=["estado"])
