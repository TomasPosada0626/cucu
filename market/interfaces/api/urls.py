from django.urls import path

from .views import (
    MisPublicacionesAPIView,
    MisPedidosAPIView,
    PedidoAceptarAPIView,
    PedidoCalificarAPIView,
    PedidoCreateAPIView,
    PedidoDetailAPIView,
    HistorialPedidosPublicAPIView,
    PedidoMarkDeliveredAPIView,
    PedidoSetPropinaAPIView,
    PublicacionDetailUpdateAPIView,
    PublicacionListCreateAPIView,
    PublicacionNearbyAPIView,
)


urlpatterns = [
    path("publicaciones", PublicacionListCreateAPIView.as_view(), name="publicaciones-list-create"),
    path("publicaciones/", PublicacionListCreateAPIView.as_view(), name="publicaciones-list-create-slash"),
    path("publicaciones/cercanas", PublicacionNearbyAPIView.as_view(), name="publicaciones-nearby"),
    path("publicaciones/cercanas/", PublicacionNearbyAPIView.as_view(), name="publicaciones-nearby-slash"),
    path("pedidos", PedidoCreateAPIView.as_view(), name="pedidos-create"),
    path("pedidos/", PedidoCreateAPIView.as_view(), name="pedidos-create-slash"),
    path("mis-pedidos", MisPedidosAPIView.as_view(), name="mis-pedidos"),
    path("mis-pedidos/", MisPedidosAPIView.as_view(), name="mis-pedidos-slash"),
    path("mis-publicaciones", MisPublicacionesAPIView.as_view(), name="mis-publicaciones"),
    path("mis-publicaciones/", MisPublicacionesAPIView.as_view(), name="mis-publicaciones-slash"),
    path("historial-pedidos", HistorialPedidosPublicAPIView.as_view(), name="historial-pedidos-public-short"),
    path("historial-pedidos/", HistorialPedidosPublicAPIView.as_view(), name="historial-pedidos-public-short-slash"),
    path("aliados/historial-pedidos", HistorialPedidosPublicAPIView.as_view(), name="aliados-historial-pedidos"),
    path("aliados/historial-pedidos/", HistorialPedidosPublicAPIView.as_view(), name="aliados-historial-pedidos-slash"),
    path("pedidos/<int:pedido_id>", PedidoDetailAPIView.as_view(), name="pedidos-detail"),
    path("pedidos/<int:pedido_id>/", PedidoDetailAPIView.as_view(), name="pedidos-detail-slash"),
    path("pedidos/<int:pedido_id>/entregar", PedidoMarkDeliveredAPIView.as_view(), name="pedidos-mark-delivered"),
    path("pedidos/<int:pedido_id>/entregar/", PedidoMarkDeliveredAPIView.as_view(), name="pedidos-mark-delivered-slash"),
    path("pedidos/<int:pedido_id>/propina", PedidoSetPropinaAPIView.as_view(), name="pedidos-set-propina"),
    path("pedidos/<int:pedido_id>/propina/", PedidoSetPropinaAPIView.as_view(), name="pedidos-set-propina-slash"),
    path("pedidos/<int:pedido_id>/calificar", PedidoCalificarAPIView.as_view(), name="pedidos-calificar"),
    path("pedidos/<int:pedido_id>/calificar/", PedidoCalificarAPIView.as_view(), name="pedidos-calificar-slash"),
    path(
        "publicaciones/<int:publicacion_id>",
        PublicacionDetailUpdateAPIView.as_view(),
        name="publicaciones-detail-update",
    ),
    path(
        "publicaciones/<int:publicacion_id>/",
        PublicacionDetailUpdateAPIView.as_view(),
        name="publicaciones-detail-update-slash",
    ),
    path("pedidos/<int:pedido_id>/aceptar/", PedidoAceptarAPIView.as_view(), name="pedidos-aceptar"),
]
