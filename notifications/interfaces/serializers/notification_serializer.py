from rest_framework import serializers

from ...infrastructure.models import Notificacion


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = [
            "id",
            "tipo",
            "mensaje",
            "fecha_envio",
            "leida",
            "usuario",
        ]
        read_only_fields = ["id", "fecha_envio"]


class PushSubscriptionInputSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2000)
    keys = serializers.DictField(child=serializers.CharField())

    def validate_keys(self, keys):
        if "p256dh" not in keys or "auth" not in keys:
            raise serializers.ValidationError("Faltan las claves p256dh/auth de la suscripción")
        return keys


class PushUnsubscribeInputSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2000)
