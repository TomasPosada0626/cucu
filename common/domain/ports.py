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
