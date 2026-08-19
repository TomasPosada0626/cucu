import json
import logging
import os
import httpx
from typing import Any
from django.conf import settings
from pywebpush import WebPushException, webpush
from ..domain.ports import (
    AllyServicePort,
    ExchangeRatePort,
    RatingServicePort,
    TransactionServicePort,
    TrustServicePort,
    WebPushExpiredError,
    WebPushPort,
)
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


class HttpSupportServiceAdapter(RatingServicePort, TrustServicePort, TransactionServicePort):
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

    def upsert_certificate(
        self, *, usuario_id: int, archivo_url: str, fecha_emision: str, estado_verificacion: bool
    ) -> dict[str, Any]:
        # Igual que create_rating: el dueño del certificado esta esperando
        # confirmacion de que se guardo, asi que un fallo aca no se traga.
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{self.base_url}/api/v3/trust/certificates",
                    json={
                        "usuario": usuario_id,
                        "archivo_url": archivo_url,
                        "fecha_emision": fecha_emision,
                        "estado_verificacion": estado_verificacion,
                    },
                )
                response.raise_for_status()
                return response.json().get("data", {})
        except Exception as exc:
            logger.warning("support_service_upsert_certificate_failed for usuario=%s", usuario_id, exc_info=True)
            raise ServiceUnavailableError("No se pudo guardar el certificado, intenta de nuevo en un momento") from exc

    def get_certificate(self, *, usuario_id: int) -> dict[str, Any] | None:
        # Lectura de estado para mostrar en el perfil: degrada en silencio,
        # tanto si no existe certificado (404) como si el servicio no responde.
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/v3/trust/certificates", params={"usuario": usuario_id})
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json().get("data")
        except Exception:
            logger.warning("support_service_get_certificate_failed for usuario=%s", usuario_id, exc_info=True)
            return None

    def upsert_transaction(
        self,
        *,
        pedido_id: int,
        fecha_cierre: str | None,
        estado: str,
        distancia_validacion_metros: float,
    ) -> dict[str, Any] | None:
        # A diferencia de create_rating/upsert_certificate, esto es
        # sincronizacion de auditoria disparada por el repartidor al
        # finalizar una entrega - no debe bloquear esa accion si
        # support-service esta caido, asi que degrada en silencio.
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{self.base_url}/api/v3/transactions",
                    json={
                        "pedido": pedido_id,
                        "fecha_cierre": fecha_cierre,
                        "estado": estado,
                        "distancia_validacion_metros": distancia_validacion_metros,
                    },
                )
                response.raise_for_status()
                return response.json().get("data")
        except Exception:
            logger.warning("support_service_upsert_transaction_failed for pedido=%s", pedido_id, exc_info=True)
            return None

    def get_transaction(self, *, pedido_id: int) -> dict[str, Any] | None:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/v3/transactions", params={"pedido": pedido_id})
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json().get("data")
        except Exception:
            logger.warning("support_service_get_transaction_failed for pedido=%s", pedido_id, exc_info=True)
            return None


class PywebpushWebPushAdapter(WebPushPort):
    def enviar(self, *, subscription: Any, titulo: str, mensaje: str) -> None:
        if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
            return

        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps({"titulo": titulo, "mensaje": mensaje}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"},
            )
        except WebPushException as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code in (404, 410):
                raise WebPushExpiredError from exc
            logger.warning("web_push_send_failed endpoint=%s", subscription.endpoint, exc_info=True)
