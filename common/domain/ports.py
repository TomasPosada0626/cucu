from abc import ABC, abstractmethod
from typing import Any

class ExchangeRatePort(ABC):
    @abstractmethod
    def get_usd_to_cop_rate(self) -> float:
        pass  # pragma: no cover

class AllyServicePort(ABC):
    @abstractmethod
    def validate_user_trust(self, user_email: str) -> dict[str, Any]:
        pass  # pragma: no cover

class RatingServicePort(ABC):
    @abstractmethod
    def create_rating(self, *, usuario_id: int, autor_id: int, puntuacion: int, comentario: str) -> dict[str, Any]:
        """Debe propagar una excepción si el servicio no responde - a
        diferencia de una lectura, silenciar un fallo aca haria creer al
        comprador que su calificacion se guardo cuando en realidad se perdio."""
        pass  # pragma: no cover

    @abstractmethod
    def list_ratings(self, *, usuario_id: int) -> list[dict[str, Any]]:
        pass  # pragma: no cover


class TrustServicePort(ABC):
    @abstractmethod
    def upsert_certificate(
        self, *, usuario_id: int, archivo_url: str, fecha_emision: str, estado_verificacion: bool
    ) -> dict[str, Any]:
        """Debe propagar una excepción si el servicio no responde - el dueño
        del certificado esta esperando confirmacion de que se guardo."""
        pass  # pragma: no cover

    @abstractmethod
    def get_certificate(self, *, usuario_id: int) -> dict[str, Any] | None:
        """None tanto si no existe certificado como si el servicio no
        responde - una lectura de estado no debe romper la pagina de perfil."""
        pass  # pragma: no cover


class TransactionServicePort(ABC):
    @abstractmethod
    def upsert_transaction(
        self,
        *,
        pedido_id: int,
        fecha_cierre: str | None,
        estado: str,
        distancia_validacion_metros: float,
    ) -> dict[str, Any] | None:
        """None si el servicio no responde - es sincronizacion de auditoria,
        no debe bloquear que el repartidor finalice la entrega."""
        pass  # pragma: no cover

    @abstractmethod
    def get_transaction(self, *, pedido_id: int) -> dict[str, Any] | None:
        pass  # pragma: no cover


class WebPushPort(ABC):
    @abstractmethod
    def enviar(self, *, subscription: Any, titulo: str, mensaje: str) -> None:
        """Debe levantar WebPushExpiredError si la suscripcion ya no es
        valida (404/410 del navegador) - el caller la borra. Cualquier otra
        falla debe tragarse: un push perdido no debe romper el flujo
        principal (crear una Notificacion, aceptar un pedido, etc.)."""
        pass  # pragma: no cover


class WebPushExpiredError(Exception):
    """La suscripcion ya no es valida (endpoint vencido/revocado)."""
