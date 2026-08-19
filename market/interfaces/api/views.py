from django.core.cache import cache
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.exceptions import NotFoundError, PermissionDeniedError, ServiceUnavailableError, ValidationError

from ...infrastructure.cache import CATALOG_CACHE_KEY, CATALOG_CACHE_TTL_SECONDS
from ...infrastructure.models import Pedido

from ...application.use_cases import (
    AcceptOrderUseCase,
    CreateOrderUseCase,
    CreatePublicacionUseCase,
    DeletePublicacionUseCase,
    GetOrderForUserUseCase,
    ListOrdersForUserUseCase,
    ListPublicacionesCercanasUseCase,
    ListPublicacionesForUserUseCase,
    ListPublicacionesUseCase,
    MarkOrderDeliveredUseCase,
    RateOrderUseCase,
    SetPropinaUseCase,
    UpdatePublicacionUseCase,
)
from ..serializers.market_serializer import (
    CalificarInputSerializer,
    PedidoCreateInputSerializer,
    PedidoOutputSerializer,
    PedidoPublicHistorySerializer,
    PropinaInputSerializer,
    PublicacionCreateInputSerializer,
    PublicacionNearbyQuerySerializer,
    PublicacionOutputSerializer,
    PublicacionUpdateInputSerializer,
)


class PublicacionListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PublicacionOutputSerializer(many=True)})
    def get(self, request):
        data = cache.get(CATALOG_CACHE_KEY)
        if data is None:
            publicaciones = ListPublicacionesUseCase().execute()
            data = PublicacionOutputSerializer(publicaciones, many=True).data
            cache.set(CATALOG_CACHE_KEY, data, CATALOG_CACHE_TTL_SECONDS)
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(request=PublicacionCreateInputSerializer, responses={201: PublicacionOutputSerializer})
    def post(self, request):
        if getattr(request.user, "es_repartidor", False):
            return Response(
                {"detail": "Las cuentas de repartidor no pueden publicar platos"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PublicacionCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            publicacion = CreatePublicacionUseCase().execute(
                user=request.user,
                **serializer.validated_data,
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PublicacionOutputSerializer(publicacion).data, status=status.HTTP_201_CREATED)


class PublicacionNearbyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[PublicacionNearbyQuerySerializer],
        responses={200: PublicacionOutputSerializer(many=True)},
    )
    def get(self, request):
        serializer = PublicacionNearbyQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        try:
            publicaciones = ListPublicacionesCercanasUseCase().execute(**serializer.validated_data)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            PublicacionOutputSerializer(publicaciones, many=True).data,
            status=status.HTTP_200_OK,
        )


class PedidoCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PedidoCreateInputSerializer, responses={201: PedidoOutputSerializer})
    def post(self, request):
        if getattr(request.user, "es_repartidor", False):
            return Response(
                {"detail": "Las cuentas de repartidor no pueden comprar pedidos"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PedidoCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pedido = CreateOrderUseCase().execute(user=request.user, **serializer.validated_data)
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PedidoOutputSerializer(pedido).data, status=status.HTTP_201_CREATED)


class PedidoDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PedidoOutputSerializer})
    def get(self, request, pedido_id: int):
        try:
            pedido = GetOrderForUserUseCase().execute(user=request.user, pedido_id=pedido_id)
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(PedidoOutputSerializer(pedido).data, status=status.HTTP_200_OK)


class PedidoMarkDeliveredAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: PedidoOutputSerializer})
    def patch(self, request, pedido_id: int):
        try:
            pedido = MarkOrderDeliveredUseCase().execute(user=request.user, pedido_id=pedido_id)
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PedidoOutputSerializer(pedido).data, status=status.HTTP_200_OK)


class PedidoSetPropinaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PropinaInputSerializer, responses={200: PedidoOutputSerializer})
    def patch(self, request, pedido_id: int):
        serializer = PropinaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pedido = SetPropinaUseCase().execute(
                user=request.user, pedido_id=pedido_id, propina=serializer.validated_data["propina"]
            )
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(PedidoOutputSerializer(pedido).data, status=status.HTTP_200_OK)


class PedidoCalificarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CalificarInputSerializer, responses={200: PedidoOutputSerializer})
    def post(self, request, pedido_id: int):
        serializer = CalificarInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pedido = RateOrderUseCase().execute(
                user=request.user,
                pedido_id=pedido_id,
                puntuacion=serializer.validated_data["puntuacion"],
                comentario=serializer.validated_data["comentario"],
            )
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(PedidoOutputSerializer(pedido).data, status=status.HTTP_200_OK)


class MisPedidosAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PedidoOutputSerializer(many=True)})
    def get(self, request):
        pedidos = ListOrdersForUserUseCase().execute(user=request.user)
        return Response(PedidoOutputSerializer(pedidos, many=True).data, status=status.HTTP_200_OK)


class MisPublicacionesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: inline_serializer(
                "MisPublicacionesOutput",
                {
                    "saldo_disponible": serializers.FloatField(),
                    "total_unidades_vendidas": serializers.IntegerField(),
                    "publicaciones": PublicacionOutputSerializer(many=True),
                },
            )
        }
    )
    def get(self, request):
        publicaciones = ListPublicacionesForUserUseCase().execute(user=request.user)
        publicaciones_data = PublicacionOutputSerializer(publicaciones, many=True).data
        saldo_disponible = round(sum(float(item.get("saldo_generado") or 0) for item in publicaciones_data), 2)
        total_unidades_vendidas = sum(int(item.get("total_vendido") or 0) for item in publicaciones_data)
        return Response(
            {
                "saldo_disponible": saldo_disponible,
                "total_unidades_vendidas": total_unidades_vendidas,
                "publicaciones": publicaciones_data,
            },
            status=status.HTTP_200_OK,
        )


class PublicacionDetailUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PublicacionUpdateInputSerializer, responses={200: PublicacionOutputSerializer})
    def patch(self, request, publicacion_id: int):
        serializer = PublicacionUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            publicacion = UpdatePublicacionUseCase().execute(
                user=request.user,
                publicacion_id=publicacion_id,
                **serializer.validated_data,
            )
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PublicacionOutputSerializer(publicacion).data, status=status.HTTP_200_OK)

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, publicacion_id: int):
        try:
            DeletePublicacionUseCase().execute(user=request.user, publicacion_id=publicacion_id)
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        return Response(status=status.HTTP_204_NO_CONTENT)


class PedidoAceptarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: PedidoOutputSerializer})
    def patch(self, request, pedido_id: int):
        try:
            pedido = AcceptOrderUseCase().execute(user=request.user, pedido_id=pedido_id)
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PedidoOutputSerializer(pedido).data, status=status.HTTP_200_OK)


class HistorialPedidosPublicAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_read"

    @extend_schema(
        responses={
            200: inline_serializer(
                "HistorialPedidosPublicOutput",
                {
                    "count": serializers.IntegerField(),
                    "limit": serializers.IntegerField(),
                    "results": PedidoPublicHistorySerializer(many=True),
                },
            )
        }
    )
    def get(self, request):
        raw_limit = request.query_params.get("limit", "50")
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            return Response({"detail": "El parametro limit debe ser numerico"}, status=status.HTTP_400_BAD_REQUEST)

        limit = max(1, min(limit, 200))
        pedidos = (
            Pedido.objects.select_related("publicacion")
            .prefetch_related("items__publicacion")
            .order_by("-fecha_creacion")[:limit]
        )

        response = Response(
            {
                "count": len(pedidos),
                "limit": limit,
                "results": PedidoPublicHistorySerializer(pedidos, many=True).data,
            },
            status=status.HTTP_200_OK,
        )
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response

    def options(self, request):
        response = Response(status=status.HTTP_200_OK)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
