from django.db import models


class RepartidorPerfil(models.Model):
    usuario = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="repartidor_perfil",
    )
    activo = models.BooleanField(default=False)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Repartidor {self.usuario_id} (activo={self.activo})"


class Asignacion(models.Model):
    ASIGNADO = "ASIGNADO"
    LLEGO_RECOGIDA = "LLEGO_RECOGIDA"
    EN_CAMINO_ENTREGA = "EN_CAMINO_ENTREGA"
    LLEGO_ENTREGA = "LLEGO_ENTREGA"
    FINALIZADO = "FINALIZADO"

    ESTADOS = [
        (ASIGNADO, "Repartidor asignado"),
        (LLEGO_RECOGIDA, "Repartidor ha llegado al restaurante"),
        (EN_CAMINO_ENTREGA, "Repartidor salio con tu pedido"),
        (LLEGO_ENTREGA, "Repartidor ha llegado a tu direccion"),
        (FINALIZADO, "Pedido finalizado"),
    ]

    pedido = models.OneToOneField(
        "market.Pedido",
        on_delete=models.CASCADE,
        related_name="asignacion",
    )
    repartidor = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="asignaciones",
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ASIGNADO)

    asignado_en = models.DateTimeField(auto_now_add=True)
    llego_recogida_en = models.DateTimeField(null=True, blank=True)
    salio_en = models.DateTimeField(null=True, blank=True)
    llego_entrega_en = models.DateTimeField(null=True, blank=True)
    finalizado_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Asignacion pedido={self.pedido_id} repartidor={self.repartidor_id} ({self.estado})"
