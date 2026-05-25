from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Rating:
    id: int
    usuario_id: int
    autor_id: int
    puntuacion: int
    comentario: str
    fecha: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "usuario": self.usuario_id,
            "autor": self.autor_id,
            "puntuacion": self.puntuacion,
            "comentario": self.comentario,
            "fecha": self.fecha,
        }


@dataclass
class Certificate:
    id: int
    usuario_id: int
    archivo_url: str
    fecha_emision: str
    estado_verificacion: bool

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "usuario": self.usuario_id,
            "archivo_url": self.archivo_url,
            "fecha_emision": self.fecha_emision,
            "estado_verificacion": self.estado_verificacion,
        }


@dataclass
class Transaction:
    id: int
    pedido_id: int
    fecha_cierre: str | None
    estado: str
    distancia_validacion_metros: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pedido": self.pedido_id,
            "fecha_cierre": self.fecha_cierre,
            "estado": self.estado,
            "distancia_validacion_metros": self.distancia_validacion_metros,
        }
