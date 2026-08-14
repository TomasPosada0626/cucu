"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include


from .web_views import (
    ui_carrito,
    ui_checkout,
    ui_seguimiento,
    ui_index,
    ui_login,
    ui_pago,
    ui_perfil,
    ui_pedido,
    ui_publicar,
    ui_recuperar_password,
    ui_registro,
    ui_restablecer_password,
    ui_aceptar_pedido,
    ui_notificaciones,
    ui_repartidor,
    ui_repartidor_entrega,
    ui_repartidor_perfil,
    ui_terminos,
    ui_privacidad,
    ui_soporte,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', ui_index, name='ui-index'),
    path('ui/registro/', ui_registro, name='ui-registro'),
    path('ui/login/', ui_login, name='ui-login'),
    path('ui/recuperar-password/', ui_recuperar_password, name='ui-recuperar-password'),
    path('ui/restablecer-password/', ui_restablecer_password, name='ui-restablecer-password'),
    path('ui/publicar/', ui_publicar, name='ui-publicar'),
    path('ui/perfil/', ui_perfil, name='ui-perfil'),
    path('ui/pedido/', ui_pedido, name='ui-pedido'),
    path('ui/carrito/', ui_carrito, name='ui-carrito'),
    path('ui/checkout/', ui_checkout, name='ui-checkout'),
    path('ui/seguimiento/', ui_seguimiento, name='ui-seguimiento'),
    path('ui/pago/', ui_pago, name='ui-pago'),
    #--------------
    path('ui/aceptar-pedido/', ui_aceptar_pedido, name='ui-aceptar-pedido'),
    path('ui/notificaciones/', ui_notificaciones, name='ui-notificaciones'),
    path('ui/repartidor/', ui_repartidor, name='ui-repartidor'),
    path('ui/repartidor/entrega/', ui_repartidor_entrega, name='ui-repartidor-entrega'),
    path('ui/repartidor/perfil/', ui_repartidor_perfil, name='ui-repartidor-perfil'),
    path('ui/terminos/', ui_terminos, name='ui-terminos'),
    path('ui/privacidad/', ui_privacidad, name='ui-privacidad'),
    path('ui/soporte/', ui_soporte, name='ui-soporte'),

    path('api/', include('notifications.interfaces.api.urls')),
    path('api/', include('geo.interfaces.api.urls')),

    path('api/', include('accounts.interfaces.api.urls')),
    path('api/', include('market.interfaces.api.urls')),
    path('api/', include('payments.interfaces.api.urls')),
    path('api/', include('common.interfaces.api.urls')),
    path('api/', include('delivery.interfaces.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

