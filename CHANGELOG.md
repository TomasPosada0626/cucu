# Changelog

Historial de lo que efectivamente se envió, en orden cronológico. La [Wiki -
Mejoras y Roadmap](../../wiki/Mejoras-y-Roadmap) mira hacia adelante (qué falta);
este archivo mira hacia atrás (qué ya se hizo). No hay versionado semántico —
CUCU no publica releases, es un fork activo — así que las entradas están
agrupadas por fecha.

## Origen (2026-02-13 a 2026-05-28)

Proyecto académico desarrollado en equipo (Laura Indaburu, Athina Cappelletti,
Tomas Posada): arquitectura inicial, modelos, historias de usuario, la
introducción de Flask/microservicios detrás de un gateway Nginx, y el primer
despliegue en AWS. Detalle completo en la Wiki (`Entregable1`, `Entregable2`).

## 2026-08-06 — Base de seguridad

- **Security:** rotados los secretos hardcodeados (`SECRET_KEY`, credenciales de
  RabbitMQ, `AUTH_JWT_SECRET`); eliminado `set_admin_pass.py` (hardcodeaba la
  contraseña del admin en texto plano); los 7 contenedores pasan a usuario no-root;
  hardening SSRF en `ConsumeExternalJsonAPIView`.
- **Added:** HTTPS real vía Let's Encrypt/sslip.io; favicon y monograma "C" de
  la marca en todas las páginas.
- **Fixed:** README (fences rotos, IP vieja, créditos).
- **Removed:** `staticfiles/`/`media/` dejan de versionarse; código muerto y
  rutas duplicadas.

## 2026-08-07 — Arquitectura limpia, mapas, repartidor real

- **Changed:** ORM de Django sacado de `domain/` en `market`, `payments` y
  `notifications` (mismo patrón que `accounts`); geocodificación/rutas migradas
  de Nominatim/Leaflet a Google Maps Platform.
- **Added:** sistema de repartidor real (`delivery` app) con máquina de 5
  estados (`ASIGNADO` → `LLEGO_RECOGIDA` → `EN_CAMINO_ENTREGA` →
  `LLEGO_ENTREGA` → `FINALIZADO`), disparada por geocerca y acciones manuales.
- **Removed:** apps `ratings`/`trust` (cascarones sin uso real).

## 2026-08-08 — Cuentas y perfil de repartidor

- **Added:** registro dividido en usuario/repartidor; dashboard de ganancias,
  historial de entregas y direcciones guardadas para el repartidor.
- **Fixed:** MIME types de nginx, healthcheck, overflow decimal en el selector
  de direcciones, ilustración del repartidor.

## 2026-08-09 — Propina y ganancia

- **Added:** `propina` persistida en `Pedido`, ganancia y distancia de entrega
  visibles para el repartidor.

## 2026-08-13 — Hardening, arquitectura, cobertura de tests

- **Security:** API y templates endurecidos contra abuso/XSS; rate-limit en
  `/admin/login/` y en `auth_microservice`; cerrado un bypass de SSRF por
  DNS-rebinding (`common/infrastructure/safe_http.py`); `validate_publicacion_imagen`
  rechaza archivos que no son una imagen raster real (XSS vía subida de SVG);
  `DEFAULT_PERMISSION_CLASSES` pasa de `AllowAny` a `IsAuthenticated`.
- **Fixed:** `auth_microservice` fallaba en una base de datos nueva ("no such
  column: nombre"); contraseñas débiles tumbaban el registro/reset con un 500
  en vez de un 400 limpio.
- **Added:** `DESIGN.md` (sistema de diseño unificado, converge el drift entre
  auth pages y app shell); suites de test para las 6 apps Django sin cobertura
  y para los 6 microservicios Flask (0% → 97–100%); cobertura medida por rama,
  no solo por sentencia. Resultado: 305 tests Django (99.6%), 313 tests de
  microservicios.
- **Removed:** scaffolding muerto (`notifications/api/`, `payments/api/`,
  `transactions/api/`, `views.py` sin usar) y un snippet de nginx desactualizado.

## 2026-08-14 — Calidad, legal, dependencias

- **Added:** `pyproject.toml` (ruff), `.pre-commit-config.yaml`, CI en GitHub
  Actions (lint + suite Django + matriz de microservicios); `SECURITY.md` +
  private vulnerability reporting habilitado en GitHub; `LICENSE` (Apache 2.0,
  Tomas Posada Suarez); páginas reales de Términos/Privacidad/Soporte
  (reemplazan 12 links muertos en 5 templates); Dependabot + job de
  `pip-audit` en CI.
- **Fixed:** imports sin usar y un `assertRaises` demasiado amplio que encontró
  ruff; la nota de "drift" en `DESIGN.md` seguía describiendo como pendiente
  algo que ya estaba convergido.
- **Security:** Pillow 10.4.0 (~17 CVEs conocidos) subido a 12.3.0; pytest 8.4.2
  (1 CVE) subido a 9.x en los 6 microservicios.

## 2026-08-15 — Docs de API, observabilidad, README

- **Added:** spec OpenAPI real del monolito vía `drf-spectacular` (Swagger UI
  en `/api/docs/`, Redoc en `/api/redoc/`, schema crudo en `/api/schema/`),
  con `@extend_schema` en las 36 vistas DRF; CI valida el schema generado.
  `/api/health/` — a diferencia del TCP-connect anterior, confirma que Django
  puede hablar con la base de datos y con Redis; el healthcheck de
  `docker-compose.yml` para el servicio `django` ahora lo usa. Logging
  estructurado (JSON, un objeto por línea) con `request_id` de correlación
  por petición (`common/infrastructure/logging.py`,
  `common.middleware.RequestIDMiddleware`), reemplazando el log de texto
  libre por defecto de Django.
- **Fixed:** dos excepciones de servicios externos que se tragaban el error en
  silencio (`common/infrastructure/adapters.py`) ahora quedan logueadas.
  README: el link de roadmap apuntaba a los Issues del repo (los 12 del curso
  original, todos cerrados) en vez de a la Wiki, que es donde realmente vive
  el tracking activo; se agregó una sección de funcionalidades, el árbol de
  Clean Architecture verificado por app, y cómo correr la suite de tests
  localmente.
