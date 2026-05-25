<!--  
se usó python -m venv venv sirve para crear un entorno virtual, esto es para almacenar 
todas las librerías de ese proyecto

venv\Scripts\activate esto es para activar el entorno virtual

pip install django djangorestframework es para descargar django, la estructura basica del framework y django rest framework es para crear la API (endpoints)

django-admin startproject config . es para crear la carpeta de config, y tiene la base del backend del proyecto

python manage.py runserver ejecutar y montar el servidor

Solucion Arquitectonica (Snippet Nginx):
```nginx
server {
        listen 80;

        location /api/v1/ {
                rewrite ^/api/v1/(.*)$ /api/$1 break;
                proxy_pass http://django:8000;
        }

        location /api/v2/payments {
                proxy_pass http://payment-service:8080;
        }

        location / {
                proxy_pass http://django:8000;
        }
}
```

Configuracion de Nginx para el taller:
- El archivo nginx.conf en la raiz enruta /api/v1/ hacia Django (servicio django:8000).
- Nginx reescribe /api/v1/... hacia /api/... porque Django hoy no usa versionado en sus URLs internas.
- La ruta estrangulada principal /api/v2/payments se envia al microservicio de pagos (servicio payment-service:8080).
- La ruta /api/v2/payments sin slash final tambien se proxyea directamente para coincidir con el endpoint POST definido en Flask.
- Se mantiene compatibilidad con /api/v2/pagos para redirigir o reescribir hacia /api/v2/payments.
- Todo el trafico restante, incluyendo /, /static/ y /media/, permanece en Django.
- La configuracion oficial de borde es nginx.conf en la raiz; la configuracion alternativa dentro de payment_microservice ya no se usa.
- Cuando integren docker-compose.yml, los nombres de servicio deben coincidir con django y payment-service o ajustar los upstreams del archivo.

Snippet sugerido para docker-compose:
- Revisar docker-compose.nginx.snippet.yml para agregar el servicio nginx cuando integren Docker.

Configuración local opcional:
- Crea un archivo `.env.local` en la raíz del proyecto.
- Para habilitar Google Maps en seguimiento y publicar, define `GOOGLE_MAPS_API_KEY=tu_api_key`.

Estos comandos fueron para crear modulos de la aplicación, ya con los archivos necesarios para agregar la logica del modulo 
python manage.py startapp accounts
python manage.py startapp trust
python manage.py startapp geo
python manage.py startapp market
python manage.py startapp payments
python manage.py startapp transactions
python manage.py startapp notifications
python manage.py startapp ratings

INSTALLED_APPS que se encuentra en: config\settings.py. Sirve para decirle a Django qué módulos están activos en el proyecto, agregué estos:

AUTH_USER_MODEL = "accounts.User" 
Es indicarle a django que usaremos un modelo personalizado, no el predeterminado que tiene django

python manage.py makemigrations accounts
python manage.py migrate

---------------------------------
NOTIFACTIONS
factories.py -> NotificacionFactory es donde esta toda la creacion de cualquier tipo de noti y lo guarda 
services.py -> NotificacionService esta toda la logica de la gestion de las notis con 
        enviar() que es crear una notificación para un usuario
        marcar_leida() busca la noti en la db y le cambia el estado
        obtener_usuario()  obtiene todas las notificaciones del usuario
serializer.py -> el objeto tipo Notificacion de models lo converte en json con id,tipo,mensaje
view.py-> Reune los emtodos anteriores solo para usarlos de acuerdo al get/post pero no calcula nada de logica del negocio
        MarcarNotificacionLeidaView() -> crea un endpoint recibe el id de la noti, llama al service y esta ya mira si esta leida-> no lo marca sino lo marca, luego la view envia el resultado en http
        MisNotificacionesView()-> toma del get se obitene el id del usrio y se buscan sus notificaciones devuelve lista de notis




HU1:
Ingresar nombre, email y contraseña: el request lo recibe RegisterInputSerializer (nombre, email, password) en serializers.py.
Guardar en base de datos: AccountService.register_user() crea el User y hace user.save() en services.py.
No permitir email duplicado: email es unique=True en el modelo y además se valida con exists() y se responde 409 (Conflict) si ya existe en models.py y services.py.
Fecha de registro automática: fecha_registro = DateTimeField(auto_now_add=True) en models.py.
Endpoint

Registro: POST /registro y POST /api/registro (ambos funcionan) en urls.py y urls.py.

HU2:

Puede ingresar email y contraseña: LoginInputSerializer recibe email + password en serializers.py.
El sistema valida credenciales: AccountService.login() usa authenticate() y si falla devuelve 401 “Credenciales inválidas” en services.py y api_views.py.
Devuelve respuesta correcta si son válidas: POST /login (y también POST /api/login) responde 200 con { token, user } en api_views.py y rutas en urls.py + urls.py.
Autenticación configurada: el proyecto está configurado con Token Authentication (DRF authtoken) como auth principal en settings.py. (Es token-based, no JWT; si necesitas específicamente JWT, lo implemento.)

HU6:

Se crea pedido asociado a publicación: OrderService.create_order() crea Pedido con publicacion=... en services.py. El modelo tiene FK publicacion en models.py.
Relacionado con usuario: el pedido se crea con usuario=request.user (JWT + IsAuthenticated) en api_views.py y FK usuario en models.py.
Estado inicial = Pendiente/Aceptado: el modelo define estado por defecto PENDIENTE en models.py (cumple la opción “Pendiente”).
Guarda fecha de creación: fecha_creacion = auto_now_add=True en models.py.
Endpoint

Ya existía POST /api/pedidos en urls.py.
Agregué alias para que también funcione POST /pedidos (y variantes con /) en:
urls.py
urls.py


HU8:

Se guarda método y monto: el modelo Pago tiene metodo y monto en models.py.
Se asocia a pedido: Pago.pedido es ForeignKey a market.Pedido y el servicio crea el pago con ese pedido en models.py y services.py.
Tiene estado (Autorizado/Fallido): PaymentService.register_payment() setea estado="AUTORIZADO" o estado="FALLIDO" según el gateway en services.py.
Endpoint

Ya existía POST /api/pagos.
Agregué alias para que también funcione POST /pago (y variantes con /) en:
urls.py
urls.py

-------------------------------
NOTIFICATIONS
factories.py -> NotificacionFactory es donde esta toda la creacion de cualquier tipo de noti y lo guarda.
        Patrón Factory: valida que el tipo sea uno de {pedido, pago, cerca, sistema} antes de crear.
        Si el tipo no es válido lanza ValueError. 

services.py -> NotificacionService esta toda la logica de la gestion de las notis con:
        enviar() que es crear una notificación para un usuario — llama a NotificacionFactory.crear()
        marcar_leida() busca la noti en la db y le cambia el estado a leida=True, si ya estaba leída lanza ValueError
        obtener_usuario() obtiene todas las notificaciones del usuario ordenadas por fecha_envio desc
api/serializers.py -> el objeto tipo Notificacion de models lo convierte en json con id, tipo, mensaje, fecha_envio, leida, usuario

views.py -> Reune los metodos anteriores solo para usarlos de acuerdo al get/post pero no calcula nada de logica del negocio
        MarcarNotificacionLeidaView() -> POST /api/notificaciones/{id}/leer/ — recibe el id de la noti, llama al service,
            el service mira si esta leida: si lo está devuelve 400, sino la marca y devuelve 200 con el objeto actualizado

        MisNotificacionesView() -> GET /api/notificaciones/ — obtiene el usuario del token JWT, busca sus notificaciones,
            devuelve lista de notis en JSON


-->

# Estado actual (microservicios)

Servicios activos en Docker Compose:

- `nginx` (puerto 80): gateway de entrada
- `django` (puerto interno 8000): UI y rutas legacy
- `payment-service` (puerto interno 8080): pagos (`/api/v2/payments`)
- `geo-service` (puerto interno 8081): geocodificacion y rutas (`/api/v2/geocode`, `/api/v2/route`)
- `notifications-service` (puerto interno 8082): notificaciones (`/api/v3/notifications`)
- `auth-service` (puerto interno 8083): autenticacion (`/api/v3/auth/*`)
- `market-service` (puerto interno 8084): publicaciones y pedidos (`/api/v3/publications`, `/api/v3/orders`)
- `support-service` (puerto interno 8085): trust/ratings/transactions (`/api/v3/trust/*`, `/api/v3/ratings`, `/api/v3/transactions`)
- `redis` (puerto interno 6379): broker/result backend para tareas Celery en Django
- `celery-worker` (sin puerto): ejecucion asincrona de tareas de dominio desde Django
- `rabbitmq` (puerto interno 5672, panel 15672): broker de mensajeria asincrona
- `notifications-worker` (sin puerto): consumidor asincrono de eventos de pago

## Matriz de cobertura por dominio (logica migrada)

Nota de contexto del equipo:

- En esta entrega se incorporaron como nuevos: `auth_microservice`, `geo_microservice`, `market_microservice`, `notifications_microservice`, `payment_microservice`.
- Se mantiene compatibilidad legacy en Django para rutas `v1` durante la transicion (Strangler Pattern), mientras que el trafico de negocio nuevo se atiende en `v2/v3`.

Metodologia de estimacion:

- Se estima la cobertura por dominio considerando endpoints productivos enroutados por Nginx a microservicios (`/api/v2`, `/api/v3`) y la logica de negocio ejecutada fuera del monolito.
- El porcentaje total se toma como promedio simple de dominios migrados.

| Dominio funcional | Modulo legacy (Django) | Microservicio nuevo (Flask) | Rutas objetivo en gateway | Cobertura estimada migrada | Hito de migracion |
|---|---|---|---|---:|---|
| Autenticacion | `accounts` | `auth_microservice` | `/api/v3/auth/*` | 90% | Entrega 02 (actual) |
| Geolocalizacion y ruteo | `geo` | `geo_microservice` | `/api/v2/geocode`, `/api/v2/route` | 90% | Entrega 02 (actual) |
| Publicaciones y pedidos | `market` | `market_microservice` | `/api/v3/publications`, `/api/v3/orders` | 80% | Entrega 02 (actual) |
| Pagos | `payments` | `payment_microservice` | `/api/v2/payments` | 85% | Entrega 02 (actual) |
| Notificaciones | `notifications` | `notifications_microservice` | `/api/v3/notifications` + worker eventos | 85% | Entrega 02 (actual) |
| Soporte (trust/ratings/transactions) | `trust`, `ratings`, `transactions` | `support_microservice` | `/api/v3/trust/*`, `/api/v3/ratings`, `/api/v3/transactions` | 90% | Entrega 02 (actual) |

**Cobertura total estimada migrada:** **86.7%**

## Comparativo legacy vs microservicio (por dominio)

| Dominio | Legacy (Django) | Microservicio (Flask) | Diferencia arquitectonica clave |
|---|---|---|---|
| Auth | `accounts` | `auth_microservice` | Pasa de autenticacion acoplada al monolito a servicio independiente enroutado por gateway (`/api/v3/auth/*`). |
| Geo | `geo` | `geo_microservice` | Geocodificacion/ruteo dejan de ejecutarse en Django y se aislan en un servicio especializado (`/api/v2/geocode`, `/api/v2/route`). |
| Market | `market` | `market_microservice` | Publicaciones y pedidos migran de app interna a API independiente (`/api/v3/publications`, `/api/v3/orders`) con despliegue y escalado desacoplado. |
| Payments | `payments` | `payment_microservice` | Registro/procesamiento de pagos se separa del monolito y publica eventos asincronos (`payment.processed`). |
| Notifications | `notifications` | `notifications_microservice` | Notificaciones pasan de logica interna Django a servicio dedicado + worker asincrono por broker. |
| Support | `trust`, `ratings`, `transactions` | `support_microservice` | Capacidades transversales de confianza/reputacion/transacciones se consolidan en servicio independiente (`/api/v3/trust/*`, `/api/v3/ratings`, `/api/v3/transactions`). |

Notas de lectura para evaluacion:

- Los modulos legacy se mantienen para compatibilidad temporal (`v1`) durante la estrategia Strangler.
- La ruta objetivo del sistema ya opera sobre microservicios (`v2/v3`) detras de Nginx API Gateway.



## Comunicacion asincrona (RabbitMQ)

- Productor: `payment-service` publica el evento `payment.processed` en la cola `payments.events` cada vez que un pago termina en `AUTORIZADO` o `FALLIDO`.
- Consumidor: `notifications-worker` consume `payments.events` y crea notificaciones tipo `pago` en `notifications-service`.
- Idempotencia: `notifications-worker` registra `event_id` en la tabla `processed_events` para evitar procesar duplicados.

Flujo de ejemplo:

1. Cliente crea pago por HTTP (`POST /api/v2/payments`).
2. `payment-service` responde al cliente y publica `payment.processed` en RabbitMQ.
3. `notifications-worker` consume el evento y guarda la notificacion asociada al usuario.
4. Cliente consulta `GET /api/v3/notifications?usuario_id=<id>` y ve la notificacion generada asincronamente.

## Comunicacion asincrona (Redis + Celery)

- Productor: `payments/domain/services.py` encola `enqueue_payment_notification.delay(...)` al registrar un pago.
- Broker: Redis (`CELERY_BROKER_URL=redis://redis:6379/0`).
- Worker: `celery-worker` ejecuta `notifications/tasks.py` y persiste la notificacion en el modelo Django `Notificacion`.
- Resultado: la API monolitica de notificaciones refleja eventos de pago procesados fuera del request HTTP.

Flujo de ejemplo:

1. Cliente crea pago (`POST /api/v1/payments`).
2. El caso de uso de pagos registra el pago y encola una tarea Celery.
3. `celery-worker` consume la tarea desde Redis y crea la notificacion.
4. Cliente consulta `GET /api/v1/notificaciones/mias` y ve la notificacion creada asincronamente.

## Internacionalizacion (ES/EN)

- Se habilito i18n nativo en Django con `LocaleMiddleware`, `LANGUAGES` y `LOCALE_PATHS`.
- Idiomas soportados: `es` y `en`.
- Seleccion de idioma soportada por Django (`i18n/` + cookie `django_language`).
- El idioma elegido se conserva entre vistas y sesiones mediante la cookie `django_language`.
- El cambio aplica de forma inmediata en la UI y no rompe la navegacion existente.
- Implementacion estricta basada en `gettext`/`{% trans %}` sin traductor por diccionario en cliente.

## Auditoria UX formal

Metodologia:

- Heuristicas de Nielsen aplicadas a flujos criticos: login/registro, compra (`pedido`), carrito, checkout, pago, seguimiento, notificaciones y perfil.
- Criterios de evaluacion: claridad de estado, prevencion de errores, consistencia visual, navegacion, control del usuario, feedback y accesibilidad basica.

Hallazgos y correcciones implementadas:

1. Visibilidad del estado del sistema
- Hallazgo: mensajes runtime en operaciones asincronas no estaban completamente estandarizados.
- Correccion: normalizacion de mensajes de procesamiento/error en vistas clave y migracion a i18n en JS inline.

2. Consistencia y estandares
- Hallazgo: coexistian variantes de textos con/sin tildes y mensajes fijos en paginas criticas.
- Correccion: unificacion de textos visibles con `{% trans %}` y constantes i18n reutilizables.

3. Prevencion de errores y robustez de formularios
- Hallazgo: validaciones de contrasena mostraban mensajes hardcoded en algunos formularios.
- Correccion: mensajes de mismatch y estado de envio centralizados y traducibles.

4. Navegacion y continuidad de flujo
- Hallazgo: faltaba evidencia formal de continuidad ante fallo parcial de servicios.
- Correccion: se documenta prueba de resiliencia con caida controlada y continuidad de home/UI.

Resultado UX esperado:

- Navegacion consistente, mensajes comprensibles en ES/EN y formularios con feedback claro durante operaciones.

## Evidencia de resiliencia en ejecucion

Mejoras de orquestacion:

- Se agregaron `healthcheck` en `docker-compose.yml` para:
        - `nginx`, `django`
        - `payment-service`, `geo-service`, `notifications-service`, `auth-service`, `market-service`, `support-service`
        - `redis`, `rabbitmq`

Prueba de caida y recuperacion controlada (ejecutada):

1. Verificacion inicial de disponibilidad
- `GET /` => `200`
- `GET /ui/pedido/` => `200`

2. Caida controlada de microservicio
- `docker compose stop support-service`

3. Validacion de continuidad del sistema
- `GET /` durante la caida de `support-service` => `200`

4. Recuperacion
- `docker compose start support-service`
- `docker compose ps support-service` => `healthy`

5. Estado general
- `docker compose ps` con servicios core arriba y saludables (o en fase `starting` dentro de su ventana de arranque).

Interpretacion:

- El gateway y el flujo principal de UI se mantienen operativos ante la caida puntual de un microservicio no critico para la ruta principal, y el servicio se recupera sin intervencion manual adicional fuera del `start` controlado.


## Evidencia de adapters (aliado y tercero)

- Adapter de aliado interno (pasarela de pagos):
        - `payments/infrastructure/gateways.py`
        - Estrategia `PaymentGatewayFactory` desacopla dominio de pagos del proveedor de autorizacion.
- Adapter de tercero (servicios de geolocalizacion/ruteo):
        - `geo/domain/services.py` (geocodificacion sobre proveedores externos)
        - `geo/infrastructure/routing.py` (rutas sobre OSRM/Valhalla con fallback)

Esta separacion permite cambiar proveedor aliado o tercero sin tocar la logica de aplicacion (use cases).

