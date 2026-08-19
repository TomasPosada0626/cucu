from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import ConflictError, NotFoundError, ValidationError

from ...application import (
    GetUserNotificationsUseCase,
    MarkNotificationAsReadUseCase,
    SubscribePushUseCase,
    UnsubscribePushUseCase,
)
from ..serializers.notification_serializer import (
    NotificacionSerializer,
    PushSubscriptionInputSerializer,
    PushUnsubscribeInputSerializer,
)


class MarcarNotificacionLeidaView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: NotificacionSerializer})
    def post(self, request, id):
        try:
            notificacion = MarkNotificationAsReadUseCase().execute(notification_id=id)
        except NotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = NotificacionSerializer(notificacion)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MisNotificacionesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: NotificacionSerializer(many=True)})
    def get(self, request):
        notificaciones = GetUserNotificationsUseCase().execute(usuario=request.user)
        serializer = NotificacionSerializer(notificaciones, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PushPublicKeyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: inline_serializer("PushPublicKeyOutput", {"publicKey": serializers.CharField()})}
    )
    def get(self, request):
        return Response({"publicKey": settings.VAPID_PUBLIC_KEY}, status=status.HTTP_200_OK)


class PushSubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PushSubscriptionInputSerializer, responses={204: None})
    def post(self, request):
        serializer = PushSubscriptionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        SubscribePushUseCase().execute(
            usuario=request.user,
            endpoint=serializer.validated_data["endpoint"],
            p256dh=serializer.validated_data["keys"]["p256dh"],
            auth=serializer.validated_data["keys"]["auth"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PushUnsubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PushUnsubscribeInputSerializer, responses={204: None})
    def post(self, request):
        serializer = PushUnsubscribeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        UnsubscribePushUseCase().execute(endpoint=serializer.validated_data["endpoint"])
        return Response(status=status.HTTP_204_NO_CONTENT)
