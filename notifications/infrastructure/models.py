from django.db import models


class Notificacion(models.Model):
    tipo = models.CharField(max_length=50)
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)

    usuario = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notificaciones"
    )

    def __str__(self):
        return f"Notificacion #{self.id} - {self.tipo}"


class PushSubscription(models.Model):
    usuario = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PushSubscription usuario={self.usuario_id}"
