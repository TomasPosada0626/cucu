from django.urls import path

from .views import (
    MarcarNotificacionLeidaView,
    MisNotificacionesView,
    PushPublicKeyView,
    PushSubscribeView,
    PushUnsubscribeView,
)


urlpatterns = [
    path("notificaciones/", MisNotificacionesView.as_view(), name="mis-notificaciones"),
    path("notificaciones/<int:id>/leer/", MarcarNotificacionLeidaView.as_view(), name="leer-notificacion"),
    path("notificaciones/push/public-key/", PushPublicKeyView.as_view(), name="push-public-key"),
    path("notificaciones/push/subscribe/", PushSubscribeView.as_view(), name="push-subscribe"),
    path("notificaciones/push/unsubscribe/", PushUnsubscribeView.as_view(), name="push-unsubscribe"),
]
