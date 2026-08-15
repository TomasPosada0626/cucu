from rest_framework import serializers

from delivery.domain.rules import haversine_meters
from market.domain.order_rules import DELIVERY_FEE_COP


class DisponibilidadInputSerializer(serializers.Serializer):
    activo = serializers.BooleanField()


class UbicacionInputSerializer(serializers.Serializer):
    latitud = serializers.FloatField(min_value=-90, max_value=90)
    longitud = serializers.FloatField(min_value=-180, max_value=180)


class PedidoCercanoOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    titulo = serializers.SerializerMethodField()
    direccion_recogida = serializers.SerializerMethodField()
    direccion_entrega = serializers.CharField()
    distancia_km = serializers.SerializerMethodField()
    distancia_entrega_km = serializers.SerializerMethodField()
    total = serializers.FloatField()
    ganancia = serializers.SerializerMethodField()

    def get_titulo(self, obj) -> str:
        return obj.publicacion.titulo

    def get_direccion_recogida(self, obj) -> str:
        ubicacion = obj.publicacion.ubicacion
        return ubicacion.direccion_texto if ubicacion else ""

    def get_distancia_km(self, obj) -> float:
        return round(float(getattr(obj, "distancia_km", 0) or 0), 2)

    def get_distancia_entrega_km(self, obj) -> float | None:
        ubicacion = obj.publicacion.ubicacion
        if not ubicacion or obj.direccion_entrega_latitud is None or obj.direccion_entrega_longitud is None:
            return None
        metros = haversine_meters(
            lat1=float(ubicacion.latitud),
            lng1=float(ubicacion.longitud),
            lat2=float(obj.direccion_entrega_latitud),
            lng2=float(obj.direccion_entrega_longitud),
        )
        return round(metros / 1000.0, 2)

    def get_ganancia(self, obj) -> float:
        return DELIVERY_FEE_COP + float(getattr(obj, "propina", 0) or 0)


class AsignacionOutputSerializer(serializers.Serializer):
    pedido_id = serializers.IntegerField()
    estado = serializers.CharField()
    direccion_recogida = serializers.SerializerMethodField()
    direccion_recogida_latitud = serializers.SerializerMethodField()
    direccion_recogida_longitud = serializers.SerializerMethodField()
    direccion_entrega = serializers.CharField(source="pedido.direccion_entrega")
    direccion_entrega_latitud = serializers.FloatField(source="pedido.direccion_entrega_latitud")
    direccion_entrega_longitud = serializers.FloatField(source="pedido.direccion_entrega_longitud")
    ganancia = serializers.SerializerMethodField()

    def get_ganancia(self, obj) -> float:
        return DELIVERY_FEE_COP + float(getattr(obj.pedido, "propina", 0) or 0)

    def get_direccion_recogida(self, obj) -> str:
        ubicacion = obj.pedido.publicacion.ubicacion
        return ubicacion.direccion_texto if ubicacion else ""

    def get_direccion_recogida_latitud(self, obj) -> float | None:
        ubicacion = obj.pedido.publicacion.ubicacion
        return float(ubicacion.latitud) if ubicacion else None

    def get_direccion_recogida_longitud(self, obj) -> float | None:
        ubicacion = obj.pedido.publicacion.ubicacion
        return float(ubicacion.longitud) if ubicacion else None


class HistorialEntregaItemSerializer(serializers.Serializer):
    pedido_id = serializers.IntegerField()
    titulo = serializers.SerializerMethodField()
    direccion_entrega = serializers.CharField(source="pedido.direccion_entrega")
    total = serializers.FloatField(source="pedido.total")
    estado = serializers.CharField()
    asignado_en = serializers.DateTimeField()
    finalizado_en = serializers.DateTimeField(allow_null=True)

    def get_titulo(self, obj) -> str:
        return obj.pedido.publicacion.titulo


class HistorialEntregasOutputSerializer(serializers.Serializer):
    total_entregas = serializers.IntegerField()
    items = HistorialEntregaItemSerializer(many=True)


class ResumenPeriodoSerializer(serializers.Serializer):
    total = serializers.FloatField()
    viajes = serializers.IntegerField()


class ResumenSemanaSerializer(ResumenPeriodoSerializer):
    proximo_pago = serializers.DateTimeField()


class ResumenRepartidorOutputSerializer(serializers.Serializer):
    hoy = ResumenPeriodoSerializer()
    semana = ResumenSemanaSerializer()


class EstadoEntregaOutputSerializer(serializers.Serializer):
    estado_entrega = serializers.CharField(allow_null=True)
    repartidor = serializers.CharField(allow_null=True)
    ubicacion = serializers.DictField(allow_null=True)
