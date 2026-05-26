from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
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
