from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Notification:
    id: int
    usuario_id: int
    tipo: str
    mensaje: str
    fecha_envio: str
    leida: bool

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "mensaje": self.mensaje,
            "fecha_envio": self.fecha_envio,
            "leida": self.leida,
            "usuario": self.usuario_id,
        }
