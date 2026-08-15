from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework import serializers, status
import json
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import connection
from urllib import error as url_error
from urllib import parse as url_parse
from urllib import request as url_request

from notifications.tasks import trigger_report_generation

from ...infrastructure.adapters import ThirdPartyExchangeRateAdapter, HttpAllyServiceAdapter
from ...infrastructure.safe_http import UnsafeHostError, build_pinned_opener, resolve_and_validate_host


class HealthAPIView(APIView):
    """Readiness real: a diferencia del TCP-connect del healthcheck de Docker
    (que solo confirma que el puerto responde), esto valida que Django puede
    hablar con la DB y con Redis. Excluido del schema de OpenAPI: es un
    endpoint de infraestructura, no parte del contrato de la API publica."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(exclude=True)
    def get(self, request):
        checks = {}
        healthy = True

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
            healthy = False

        try:
            cache.set("health_check_probe", "ok", timeout=5)
            cache.get("health_check_probe")
            checks["cache"] = "ok"
        except Exception:
            checks["cache"] = "error"
            healthy = False

        status_code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {"status": "ok" if healthy else "error", "checks": checks},
            status=status_code,
        )


class ExternalServicesTestAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "external"

    @extend_schema(
        responses={
            200: inline_serializer(
                "ExternalServicesTestOutput",
                {
                    "status": serializers.CharField(),
                    "message": serializers.CharField(),
                    "adapters": serializers.JSONField(),
                },
            )
        }
    )
    def get(self, request):
        exchange_adapter = ThirdPartyExchangeRateAdapter()
        ally_adapter = HttpAllyServiceAdapter()

        # Usar el adaptador 1 (Terceros)
        usd_rate = exchange_adapter.get_usd_to_cop_rate()

        # Usar el adaptador 2 (Servicio Aliado)
        email = request.query_params.get("email", "test@example.com")
        ally_data = ally_adapter.validate_user_trust(email)

        return Response({
            "status": "success",
            "message": "Endpoint propio que consume servicios externos mediante Patrón Adapter",
            "adapters": {
                "exchange_rate_api": {
                    "provider": "Exchangerate-api.com",
                    "usd_to_cop": usd_rate,
                },
                "ally_service": ally_data
            }
        }, status=status.HTTP_200_OK)



class TriggerAsyncTaskAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "external"

    @extend_schema(
        request=inline_serializer("TriggerAsyncTaskInput", {"email": serializers.EmailField(required=False)}),
        responses={
            202: inline_serializer(
                "TriggerAsyncTaskOutput",
                {
                    "status": serializers.CharField(),
                    "message": serializers.CharField(),
                    "task_id": serializers.CharField(),
                },
            )
        },
    )
    def post(self, request):
        email = request.data.get("email", "test@example.com")
        try:
            validate_email(email)
        except DjangoValidationError:
            return Response({"detail": "El parametro email no es valido"}, status=status.HTTP_400_BAD_REQUEST)

        task = trigger_report_generation.delay(requester_email=email)
        return Response({
            "status": "success",
            "message": "Tarea asíncrona iniciada correctamente.",
            "task_id": task.id
        }, status=status.HTTP_202_ACCEPTED)


class ConsumeExternalJsonAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "external"

    _request_serializer = inline_serializer("ConsumeExternalJsonInput", {"url": serializers.CharField()})
    _response_serializer = inline_serializer(
        "ConsumeExternalJsonOutput",
        {
            "ok": serializers.BooleanField(),
            "url": serializers.CharField(),
            "status_code": serializers.IntegerField(),
            "data": serializers.JSONField(),
        },
    )

    @staticmethod
    def _validate_url(raw_url: str) -> tuple[str, str]:
        """Devuelve (url, ip_validada). La IP se resuelve una sola vez aqui y
        el caller debe conectar contra ella directamente (ver safe_http) en
        vez de dejar que la libreria HTTP repita la resolucion DNS - si no,
        el chequeo de host privado se puede saltar con DNS rebinding."""
        candidate = str(raw_url or "").strip()
        if not candidate:
            raise ValueError("Debes enviar una URL")

        parsed = url_parse.urlparse(candidate)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("La URL debe iniciar con http:// o https://")
        if not parsed.netloc:
            raise ValueError("La URL no es valida")

        host = (parsed.hostname or "").lower()
        if not host:
            raise ValueError("La URL no es valida")

        try:
            resolved_ip = resolve_and_validate_host(host)
        except UnsafeHostError as exc:
            raise ValueError(str(exc)) from exc

        return candidate, resolved_ip

    @extend_schema(request=_request_serializer, responses={200: _response_serializer})
    def post(self, request):
        try:
            target_url, resolved_ip = self._validate_url(request.data.get("url"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        req = url_request.Request(
            target_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "CUCU-ally-client/1.0",
            },
            method="GET",
        )

        opener = build_pinned_opener(resolved_ip)

        try:
            with opener.open(req, timeout=10) as response:
                body = response.read().decode("utf-8", errors="replace")
                payload = json.loads(body)
                return Response(
                    {
                        "ok": True,
                        "url": target_url,
                        "status_code": int(getattr(response, "status", 200)),
                        "data": payload,
                    },
                    status=status.HTTP_200_OK,
                )
        except json.JSONDecodeError:
            return Response(
                {"detail": "La respuesta del aliado no es JSON valido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except url_error.HTTPError as exc:
            return Response(
                {
                    "detail": "El servicio aliado respondio con error HTTP",
                    "ally_status": int(exc.code),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except (url_error.URLError, TimeoutError):
            return Response(
                {"detail": "No fue posible conectar con la URL aliada"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
