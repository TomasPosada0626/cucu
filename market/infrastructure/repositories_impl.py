from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import F, FloatField, Sum, Value
from django.db.models.functions import Coalesce

from common.exceptions import NotFoundError

from ..domain.order_rules import PublicacionSnapshot, validate_and_price_items
from .models import Pedido, PedidoItem, Publicacion


class DjangoPublicacionRepository:
    def list_all(self):
        return Publicacion.objects.select_related("ubicacion", "usuario").all().order_by("-id")

    def list_active_with_location(self):
        return (
            Publicacion.objects.select_related("ubicacion", "usuario")
            .filter(estado="ACTIVA", ubicacion__isnull=False)
            .order_by("-id")
        )

    def list_for_user(self, user):
        line_total = F("pedido_items__cantidad") * F("pedido_items__precio_unitario")
        return (
            Publicacion.objects.select_related("ubicacion", "usuario")
            .filter(usuario=user)
            .annotate(
                total_vendido=Coalesce(Sum("pedido_items__cantidad"), 0),
                saldo_generado=Coalesce(Sum(line_total, output_field=FloatField()), Value(0.0)),
            )
            .order_by("-fecha_publicacion", "-id")
        )

    def get_by_id(self, publicacion_id: int) -> Publicacion | None:
        return Publicacion.objects.select_related("ubicacion", "usuario").filter(id=publicacion_id).first()

    def create(self, **fields: Any) -> Publicacion:
        return Publicacion.objects.create(**fields)

    def update(self, publicacion: Publicacion, **changes: Any) -> None:
        update_fields = list(changes.keys())
        for field, value in changes.items():
            setattr(publicacion, field, value)
        publicacion.save(update_fields=update_fields)

    def delete(self, publicacion: Publicacion) -> None:
        publicacion.delete()


class DjangoPedidoRepository:
    TERMINAL_ORDER_STATES = {"ENTREGADO", "FINALIZADO", "COMPLETADO", "CANCELADO"}

    def get_active_for_user(self, user) -> Pedido | None:
        return (
            Pedido.objects.filter(usuario=user)
            .exclude(estado__in=self.TERMINAL_ORDER_STATES)
            .order_by("-fecha_creacion")
            .first()
        )

    def get_for_user(self, user, pedido_id: int) -> Pedido | None:
        return Pedido.objects.prefetch_related("items__publicacion").filter(
            id=pedido_id, usuario=user
        ).first()

    def get_by_id_with_relations(self, pedido_id: int) -> Pedido | None:
        return Pedido.objects.select_related("publicacion", "usuario").filter(id=pedido_id).first()

    def list_for_user(self, user):
        return (
            Pedido.objects.prefetch_related("items__publicacion", "pagos")
            .filter(usuario=user)
            .order_by("-fecha_creacion")
        )

    def mark_delivered(self, pedido: Pedido) -> None:
        pedido.estado = "ENTREGADO"
        pedido.save(update_fields=["estado"])

    def mark_calificado(self, pedido: Pedido) -> None:
        pedido.calificado = True
        pedido.save(update_fields=["calificado"])

    def save_estado(self, pedido: Pedido) -> None:
        pedido.save(update_fields=["estado"])

    def set_propina(self, pedido: Pedido, propina: float) -> None:
        pedido.propina = max(0.0, float(propina or 0))
        pedido.save(update_fields=["propina"])

    def create_order(
        self,
        *,
        user,
        telefono: str,
        direccion_entrega: str,
        direccion_entrega_detalles: str,
        direccion_entrega_latitud: Decimal | None,
        direccion_entrega_longitud: Decimal | None,
        counts: dict[int, int],
    ) -> Pedido:
        with transaction.atomic():
            publicaciones = list(
                Publicacion.objects.select_for_update()
                .select_related("usuario")
                .filter(id__in=list(counts.keys()))
            )
            if len(publicaciones) != len(counts):
                found_ids = {p.id for p in publicaciones}
                missing = [pid for pid in counts if pid not in found_ids]
                raise NotFoundError(f"Publicación no encontrada: {missing[0]}")

            publicaciones_by_id = {p.id: p for p in publicaciones}
            snapshots = {
                pid: PublicacionSnapshot(
                    id=p.id,
                    titulo=p.titulo,
                    estado=p.estado or "",
                    stock=int(p.stock or 0),
                    maximo_por_venta=int(p.maximo_por_venta or 1),
                    precio=float(p.precio),
                )
                for pid, p in publicaciones_by_id.items()
            }

            computed_total = validate_and_price_items(counts, snapshots)

            first_publicacion = publicaciones_by_id[next(iter(counts.keys()))]
            pedido = Pedido.objects.create(
                usuario=user,
                publicacion=first_publicacion,
                telefono=telefono,
                direccion_entrega=direccion_entrega,
                direccion_entrega_detalles=direccion_entrega_detalles,
                direccion_entrega_latitud=direccion_entrega_latitud,
                direccion_entrega_longitud=direccion_entrega_longitud,
                total=computed_total,
            )

            for pub_id, qty in counts.items():
                pub = publicaciones_by_id[pub_id]
                PedidoItem.objects.create(
                    pedido=pedido,
                    publicacion=pub,
                    cantidad=qty,
                    precio_unitario=float(pub.precio),
                )
                pub.stock = max(0, int(pub.stock or 0) - qty)
                pub.save(update_fields=["stock"])

            return pedido


class DjangoUbicacionRepository:
    def create(self, **fields: Any):
        from geo.infrastructure.models import Ubicacion

        return Ubicacion.objects.create(**fields)

    def delete_if_orphan(self, ubicacion) -> None:
        if ubicacion is not None and not ubicacion.publicaciones.exists():
            ubicacion.delete()
