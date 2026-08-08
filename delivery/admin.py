from django.contrib import admin

from .infrastructure.models import Asignacion, RepartidorPerfil


@admin.register(RepartidorPerfil)
class RepartidorPerfilAdmin(admin.ModelAdmin):
    list_display = ("usuario", "activo", "latitud", "longitud", "actualizado_en")


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ("pedido", "repartidor", "estado", "asignado_en", "finalizado_en")
    list_filter = ("estado",)
