from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Publication:
    id: int
    autor_id: int
    titulo: str
    descripcion: str
    precio: float
    disponibilidad: bool
    direccion_texto: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "autor_id": self.autor_id,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "precio": self.precio,
            "disponibilidad": self.disponibilidad,
            "direccion_texto": self.direccion_texto,
        }


@dataclass
class Order:
    id: int
    publicacion_id: int
    comprador_id: int
    cantidad: int
    total: float
    estado: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "publicacion_id": self.publicacion_id,
            "comprador_id": self.comprador_id,
            "cantidad": self.cantidad,
            "total": self.total,
            "estado": self.estado,
        }
