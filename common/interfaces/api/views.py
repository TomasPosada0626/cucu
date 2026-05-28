from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json
from urllib import error as url_error
from urllib import parse as url_parse
from urllib import request as url_request

from ...infrastructure.adapters import ThirdPartyExchangeRateAdapter, HttpAllyServiceAdapter

class ExternalServicesTestAPIView(APIView):
    authentication_classes = []
    permission_classes = []

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


from notifications.tasks import trigger_report_generation

class TriggerAsyncTaskAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get("email", "test@example.com")
        task = trigger_report_generation.delay(requester_email=email)
        return Response({
            "status": "success",
            "message": "Tarea asíncrona iniciada correctamente.",
            "task_id": task.id
        }, status=status.HTTP_202_ACCEPTED)


class ConsumeExternalJsonAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @staticmethod
    def _validate_url(raw_url: str) -> str:
        candidate = str(raw_url or "").strip()
        if not candidate:
            raise ValueError("Debes enviar una URL")

        parsed = url_parse.urlparse(candidate)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("La URL debe iniciar con http:// o https://")
        if not parsed.netloc:
            raise ValueError("La URL no es valida")

        host = (parsed.hostname or "").lower()
        if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            raise ValueError("No se permite consumir hosts locales")
        return candidate

    def post(self, request):
        try:
            target_url = self._validate_url(request.data.get("url"))
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

        try:
            with url_request.urlopen(req, timeout=10) as response:
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
