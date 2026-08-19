import logging
import os
import httpx
from typing import Any
from ..domain.ports import ExchangeRatePort, AllyServicePort, RatingServicePort
from ..exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)


class ThirdPartyExchangeRateAdapter(ExchangeRatePort):
    def get_usd_to_cop_rate(self) -> float:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get("https://api.exchangerate-api.com/v4/latest/USD")
                response.raise_for_status()
                data = response.json()
                return data.get("rates", {}).get("COP", 4000.0)
        except Exception:
            logger.warning("exchange_rate_fetch_failed, using fallback rate", exc_info=True)
            return 4000.0


class HttpAllyServiceAdapter(AllyServicePort):
    def __init__(self):
        self.base_url = os.environ.get("ALLY_SERVICE_URL", "").rstrip("/")

    def validate_user_trust(self, user_email: str) -> dict[str, Any]:
        # Fallback/Mock documentado como lo pide el Entregable 2
        if not self.base_url:
            return {
                "status": "verified",
                "score": 85,
                "email": user_email,
                "mocked": True,
                "message": "Fallback applied. Configure ALLY_SERVICE_URL to connect to real service."
            }

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(f"{self.base_url}/api/validate", json={"email": user_email})
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning("ally_service_validation_failed for %s", user_email, exc_info=True)
            return {
                "status": "unknown",
                "score": 0,
                "email": user_email,
                "mocked": False,
                "error": str(e)
            }


class HttpSupportServiceAdapter(RatingServicePort):
    def __init__(self):
        # A diferencia de ALLY_SERVICE_URL (integracion externa opcional),
        # support-service es interno al docker-compose - mismo default-que-
        # funciona-solo que GEO_SERVICE_URL/NOTIFICATIONS_SERVICE_URL.
        self.base_url = os.environ.get("SUPPORT_SERVICE_URL", "http://support-service:8085").rstrip("/")

    def create_rating(self, *, usuario_id: int, autor_id: int, puntuacion: int, comentario: str) -> dict[str, Any]:
        # A diferencia de list_ratings, un fallo aca NO se traga: el
        # comprador esta esperando confirmacion de que su calificacion se
        # guardo. Devolver éxito igual seria mentirle - mejor un 503 claro
        # que el caller pueda mostrar, y el comprador reintenta.
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{self.base_url}/api/v3/ratings",
                    json={
                        "usuario": usuario_id,
                        "autor": autor_id,
                        "puntuacion": puntuacion,
                        "comentario": comentario,
                    },
                )
                response.raise_for_status()
                return response.json().get("data", {})
        except Exception as exc:
            logger.warning("support_service_create_rating_failed for usuario=%s", usuario_id, exc_info=True)
            raise ServiceUnavailableError("No se pudo guardar la calificación, intenta de nuevo en un momento") from exc

    def list_ratings(self, *, usuario_id: int) -> list[dict[str, Any]]:
        # Esta si degrada en silencio: alimenta un promedio informativo
        # (reputacion_promedio), no una confirmacion que el usuario este
        # esperando. Mejor mostrar el ultimo promedio conocido que romper
        # la pagina de perfil por esto.
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/v3/ratings", params={"usuario": usuario_id})
                response.raise_for_status()
                return response.json().get("data", [])
        except Exception:
            logger.warning("support_service_list_ratings_failed for usuario=%s", usuario_id, exc_info=True)
            return []
