from __future__ import annotations

from .models import User


class DjangoUserRepository:
    _PEDIDO_ESTADO_TERMINAL = "ENTREGADO"
    _ASIGNACION_ESTADO_TERMINAL = "FINALIZADO"

    def exists_by_email(self, email: str) -> bool:
        return User.objects.filter(email=email).exists()

    def get_by_email(self, email: str) -> User | None:
        return User.objects.filter(email=email).first()

    def get_by_id(self, user_id: int) -> User | None:
        return User.objects.filter(id=user_id).first()

    def create_user(self, *, nombre: str, email: str, password: str, es_repartidor: bool = False) -> User:
        user = User(
            username=email,
            email=email,
            nombre=nombre,
            es_repartidor=es_repartidor,
        )
        user.set_password(password)
        user.save()
        return user

    def update_password(self, *, user: User, password: str) -> User:
        user.set_password(password)
        user.save(update_fields=["password"])
        return user

    def find_deletion_blocker(self, *, user: User) -> str | None:
        from delivery.infrastructure.models import Asignacion
        from market.infrastructure.models import Pedido

        if Pedido.objects.filter(usuario=user).exclude(estado=self._PEDIDO_ESTADO_TERMINAL).exists():
            return "Tienes pedidos activos como comprador. Espera a que se entreguen antes de eliminar tu cuenta."

        if Pedido.objects.filter(publicacion__usuario=user).exclude(estado=self._PEDIDO_ESTADO_TERMINAL).exists():
            return (
                "Tienes pedidos activos en tus publicaciones. Espera a que se entreguen "
                "antes de eliminar tu cuenta."
            )

        if Asignacion.objects.filter(repartidor=user).exclude(estado=self._ASIGNACION_ESTADO_TERMINAL).exists():
            return "Tienes una entrega activa asignada. Finalizala antes de eliminar tu cuenta."

        return None

    def delete_user(self, *, user: User) -> None:
        for publicacion in user.publicaciones.all():
            if publicacion.imagen:
                publicacion.imagen.delete(save=False)
        user.delete()

    def export_user_data(self, *, user: User) -> dict:
        from delivery.infrastructure.models import Asignacion
        from market.infrastructure.models import Pedido

        repartidor_perfil = None
        asignaciones: list = []
        if hasattr(user, "repartidor_perfil"):
            perfil = user.repartidor_perfil
            repartidor_perfil = {
                "activo": perfil.activo,
                "latitud": perfil.latitud,
                "longitud": perfil.longitud,
                "actualizado_en": perfil.actualizado_en,
            }
            asignaciones = list(
                Asignacion.objects.filter(repartidor=user).values(
                    "id", "pedido_id", "estado", "asignado_en", "finalizado_en"
                )
            )

        return {
            "perfil": {
                "id": user.id,
                "nombre": user.nombre,
                "email": user.email,
                "fecha_registro": user.fecha_registro,
                "es_repartidor": user.es_repartidor,
                "reputacion_promedio": user.reputacion_promedio,
                "total_ventas": user.total_ventas,
                "total_compras": user.total_compras,
            },
            "direcciones_guardadas": list(
                user.direcciones_guardadas.values(
                    "id", "nombre", "direccion_texto", "detalles",
                    "latitud", "longitud", "es_predeterminada", "creado_en",
                )
            ),
            "publicaciones": list(
                user.publicaciones.values(
                    "id", "titulo", "descripcion", "categoria", "precio",
                    "stock", "estado", "fecha_publicacion",
                )
            ),
            "pedidos_como_comprador": list(
                Pedido.objects.filter(usuario=user).values(
                    "id", "estado", "total", "propina", "telefono",
                    "direccion_entrega", "fecha_creacion",
                )
            ),
            "pedidos_en_mis_publicaciones": list(
                Pedido.objects.filter(publicacion__usuario=user).values(
                    "id", "estado", "total", "fecha_creacion", "publicacion_id",
                )
            ),
            "notificaciones": list(
                user.notificaciones.values("id", "tipo", "mensaje", "fecha_envio", "leida")
            ),
            "repartidor_perfil": repartidor_perfil,
            "asignaciones_como_repartidor": asignaciones,
        }
