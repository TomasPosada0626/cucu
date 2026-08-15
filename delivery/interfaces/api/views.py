from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError

from ...application import (
    AceptarPedidoUseCase,
    ActualizarUbicacionUseCase,
    AsignacionActivaUseCase,
    EstadoParaCompradorUseCase,
    HistorialEntregasUseCase,
    ListarPedidosCercanosUseCase,
    MarcarFinalizadoUseCase,
    MarcarSalioUseCase,
    ResumenRepartidorUseCase,
    SetDisponibilidadUseCase,
)
from ..serializers.delivery_serializer import (
    AsignacionOutputSerializer,
    DisponibilidadInputSerializer,
    EstadoEntregaOutputSerializer,
    HistorialEntregasOutputSerializer,
    PedidoCercanoOutputSerializer,
    ResumenRepartidorOutputSerializer,
    UbicacionInputSerializer,
)
from .permissions import IsRepartidor


class DisponibilidadAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRepartidor]

    @extend_schema(
        request=DisponibilidadInputSerializer,
        responses={200: inline_serializer("DisponibilidadOutput", {"activo": serializers.BooleanField()})},
    )
    def post(self, request):
        serializer = DisponibilidadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        perfil = SetDisponibilidadUseCase().execute(
            usuario=request.user, activo=serializer.validated_data["activo"]
        )
        return Response({"activo": perfil.activo}, status=status.HTTP_200_OK)


class PedidosCercanosAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRepartidor]

    @extend_schema(
        responses={
            200: inline_serializer(
                "PedidosCercanosOutput", {"items": PedidoCercanoOutputSerializer(many=True)}
            )
        }
    )
    def get(self, request):
        try:
            pedidos = ListarPedidosCercanosUseCase().execute(usuario=request.user)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"items": PedidoCercanoOutputSerializer(pedidos, many=True).data},
            status=status.HTTP_200_OK,
        )


class AceptarPedidoAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRepartidor]

    @extend_schema(request=None, responses={201: AsignacionOutputSerializer})
    def post(self, request, pedido_id: int):
        try:
            asignacion = AceptarPedidoUseCase().execute(usuario=request.user, pedido_id=pedido_id)
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(AsignacionOutputSerializer(asignacion).data, status=status.HTTP_201_CREATED)


class UbicacionAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRepartidor]

    @extend_schema(
        request=UbicacionInputSerializer,
        responses={
            200: inline_serializer(
                "UbicacionEntregaOutput",
                {"asignacion": AsignacionOutputSerializer(required=False, allow_null=True)},
            )
        },
    )
    def post(self, request):
        serializer = UbicacionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = ActualizarUbicacionUseCase().execute(
            usuario=request.user,
            latitud=serializer.validated_data["latitud"],
            longitud=serializer.validated_data["longitud"],
        )
        asignacion = result.get("asignacion")
        data = AsignacionOutputSerializer(asignacion).data if asignacion else None
        return Response({"asignacion": data}, status=status.HTTP_200_OK)


class AsignacionActivaAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRepartidor]

    @extend_schema(
        responses={
            200: inline_serializer(
                "AsignacionActivaOutput",
                {"asignacion": AsignacionOutputSerializer(required=False, allow_null=True)},
            )
        }
    )
    def get(self, request):
        asignacion = AsignacionActivaUseCase().execute(usuario=request.user)
        data = AsignacionOutputSerializer(asignacion).data if asignacion else None
        return Response({"asignacion": data}, status=status.HTTP_200_OK)


class MarcarSalioAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRepartidor]

    @extend_schema(request=None, responses={200: AsignacionOutputSerializer})
    def post(self, request, pedido_id: int):
        try:
            asignacion = MarcarSalioUseCase().execute(usuario=request.user, pedido_id=pedido_id)
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(AsignacionOutputSerializer(asignacion).data, status=status.HTTP_200_OK)


class MarcarFinalizadoAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRepartidor]

    @extend_schema(request=None, responses={200: AsignacionOutputSerializer})
    def post(self, request, pedido_id: int):
        try:
            asignacion = MarcarFinalizadoUseCase().execute(usuario=request.user, pedido_id=pedido_id)
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(AsignacionOutputSerializer(asignacion).data, status=status.HTTP_200_OK)


class HistorialEntregasAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRepartidor]

    @extend_schema(responses={200: HistorialEntregasOutputSerializer})
    def get(self, request):
        data = HistorialEntregasUseCase().execute(usuario=request.user)
        return Response(HistorialEntregasOutputSerializer(data).data, status=status.HTTP_200_OK)


class ResumenRepartidorAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRepartidor]

    @extend_schema(responses={200: ResumenRepartidorOutputSerializer})
    def get(self, request):
        data = ResumenRepartidorUseCase().execute(usuario=request.user)
        return Response(ResumenRepartidorOutputSerializer(data).data, status=status.HTTP_200_OK)


class EstadoEntregaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: EstadoEntregaOutputSerializer})
    def get(self, request, pedido_id: int):
        try:
            data = EstadoParaCompradorUseCase().execute(usuario=request.user, pedido_id=pedido_id)
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(EstadoEntregaOutputSerializer(data).data, status=status.HTTP_200_OK)
