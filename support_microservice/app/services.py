from __future__ import annotations

from .errors import NotFoundError, ValidationError
from .repositories.support_repository import SQLiteSupportRepository


class SupportService:
    def __init__(self, *, repository: SQLiteSupportRepository) -> None:
        self.repository = repository

    def create_rating(self, *, usuario_id: int, autor_id: int, puntuacion: int, comentario: str) -> dict:
        if int(usuario_id or 0) <= 0 or int(autor_id or 0) <= 0:
            raise ValidationError("Usuario y autor son obligatorios")
        if int(puntuacion) < 1 or int(puntuacion) > 5:
            raise ValidationError("La puntuacion debe estar entre 1 y 5")
        normalized_comment = str(comentario or "").strip()
        if not normalized_comment:
            raise ValidationError("El comentario es obligatorio")

        rating = self.repository.create_rating(
            usuario_id=int(usuario_id),
            autor_id=int(autor_id),
            puntuacion=int(puntuacion),
            comentario=normalized_comment,
        )
        return rating.to_dict()

    def list_ratings(self, *, usuario_id: int) -> list[dict]:
        if int(usuario_id or 0) <= 0:
            raise ValidationError("Usuario invalido")
        return [item.to_dict() for item in self.repository.list_ratings_for_user(usuario_id=int(usuario_id))]

    def upsert_certificate(
        self,
        *,
        usuario_id: int,
        archivo_url: str,
        fecha_emision: str,
        estado_verificacion: bool,
    ) -> dict:
        if int(usuario_id or 0) <= 0:
            raise ValidationError("Usuario invalido")
        if not str(archivo_url or "").strip():
            raise ValidationError("archivo_url es obligatorio")
        if not str(fecha_emision or "").strip():
            raise ValidationError("fecha_emision es obligatoria")

        cert = self.repository.upsert_certificate(
            usuario_id=int(usuario_id),
            archivo_url=str(archivo_url).strip(),
            fecha_emision=str(fecha_emision).strip(),
            estado_verificacion=bool(estado_verificacion),
        )
        return cert.to_dict()

    def get_certificate(self, *, usuario_id: int) -> dict:
        cert = self.repository.get_certificate_by_user(int(usuario_id))
        if cert is None:
            raise NotFoundError("Certificado no encontrado")
        return cert.to_dict()

    def upsert_transaction(
        self,
        *,
        pedido_id: int,
        fecha_cierre: str | None,
        estado: str,
        distancia_validacion_metros: float,
    ) -> dict:
        if int(pedido_id or 0) <= 0:
            raise ValidationError("pedido_id invalido")
        normalized_estado = str(estado or "").strip().upper() or "ABIERTA"
        tx = self.repository.upsert_transaction(
            pedido_id=int(pedido_id),
            fecha_cierre=str(fecha_cierre).strip() if fecha_cierre else None,
            estado=normalized_estado,
            distancia_validacion_metros=float(distancia_validacion_metros or 0.0),
        )
        return tx.to_dict()

    def get_transaction(self, *, pedido_id: int) -> dict:
        try:
            pedido_id_int = int(pedido_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError("pedido_id invalido") from exc

        if pedido_id_int <= 0:
            raise ValidationError("pedido_id invalido")

        tx = self.repository.get_transaction_by_order(pedido_id_int)
        if tx is None:
            raise NotFoundError("Transaccion no encontrada")
        return tx.to_dict()
