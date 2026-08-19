from django.urls import path

from .views import (
    AceptarPedidoAPIView,
    AsignacionActivaAPIView,
    DisponibilidadAPIView,
    EstadoEntregaAPIView,
    HistorialEntregasAPIView,
    MarcarFinalizadoAPIView,
    MarcarSalioAPIView,
    PedidosCercanosAPIView,
    RechazarPedidoAPIView,
    ResumenRepartidorAPIView,
    UbicacionAPIView,
)

urlpatterns = [
    path("repartidor/disponibilidad", DisponibilidadAPIView.as_view(), name="repartidor-disponibilidad"),
    path("repartidor/pedidos-cercanos", PedidosCercanosAPIView.as_view(), name="repartidor-pedidos-cercanos"),
    path("repartidor/asignacion-activa", AsignacionActivaAPIView.as_view(), name="repartidor-asignacion-activa"),
    path("repartidor/pedidos/<int:pedido_id>/aceptar", AceptarPedidoAPIView.as_view(), name="repartidor-aceptar"),
    path("repartidor/pedidos/<int:pedido_id>/rechazar", RechazarPedidoAPIView.as_view(), name="repartidor-rechazar"),
    path("repartidor/ubicacion", UbicacionAPIView.as_view(), name="repartidor-ubicacion"),
    path("repartidor/pedidos/<int:pedido_id>/salio", MarcarSalioAPIView.as_view(), name="repartidor-salio"),
    path("repartidor/pedidos/<int:pedido_id>/finalizar", MarcarFinalizadoAPIView.as_view(), name="repartidor-finalizar"),
    path("repartidor/historial", HistorialEntregasAPIView.as_view(), name="repartidor-historial"),
    path("repartidor/resumen", ResumenRepartidorAPIView.as_view(), name="repartidor-resumen"),
    path("pedidos/<int:pedido_id>/estado-entrega", EstadoEntregaAPIView.as_view(), name="pedido-estado-entrega"),
]
