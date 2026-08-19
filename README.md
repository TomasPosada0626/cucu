# CUCU — Comida casera en cocas cerca de ti

<img width="1191" height="707" alt="image" src="https://github.com/user-attachments/assets/dc99b69f-c6b5-45a6-9abd-fae4f4a72edf" />

CUCU es un marketplace local de comida casera: conecta a personas que tienen porciones adicionales de comida ("cocas") con usuarios cercanos que buscan una alternativa rápida, económica y casera para alimentarse. La ubicación geográfica es el eje del producto: publicaciones, notificaciones y cierre de la transacción dependen de la cercanía entre comprador y vendedor.

El proyecto está construido con un modelo híbrido: **Django (monolito para vistas y lógica central) + Flask (microservicios especializados)**, con **RabbitMQ** y **Redis** como servicios de apoyo. Todo se orquesta con **Docker Compose** y se expone a través de un **API Gateway (Nginx)**.

Más contexto de negocio y las entregas académicas del proyecto están en la [Wiki](../../wiki).

## Funcionalidades principales

- **Cuentas:** registro, login (JWT + token), recuperación de contraseña, direcciones guardadas.
- **Marketplace:** publicar "cocas" con imagen/stock, buscar publicaciones cercanas por geolocalización, carrito y pedidos.
- **Delivery:** repartidores marcan disponibilidad, ven pedidos cercanos, aceptan y actualizan el estado de una entrega en tiempo real (ubicación, salida, finalizado).
- **Pagos:** registro de pagos por pedido, historial y saldo del vendedor.
- **Notificaciones:** notificaciones in-app por eventos del pedido (aceptado, en camino, entregado).
- **Soporte:** calificaciones entre usuarios y certificados de confianza.

## Estado del proyecto

Este repo es un fork activo mantenido por [@TomasPosada0626](https://github.com/TomasPosada0626) a partir del trabajo original en equipo. La hoja de ruta de mejoras en curso vive en la wiki, en [Mejoras y Roadmap](../../wiki/Mejoras-y-Roadmap) (seguridad, arquitectura limpia, tests, microservicios) — los [Issues](../../issues) del repo son los entregables cerrados del curso original, no el tracking activo.

## Requisitos Previos

- Docker y Docker Compose instalados.
- Clonar este repositorio.

## Ejecución Local con Docker Compose

1. **Configurar Variables de Entorno**
   Copia el archivo de ejemplo para crear tus variables locales. **Nunca comitees `.env`** — ya está en `.gitignore`, y tanto Django como Docker Compose lo leen automáticamente:
   ```bash
   cp .env.example .env
   ```
   Ajusta al menos `SECRET_KEY`, `AUTH_JWT_SECRET` y `RABBITMQ_PASSWORD` con valores propios (no dejes los placeholders del ejemplo si vas a exponer el servicio).

2. **Levantar el Ecosistema**
   Ejecuta el siguiente comando en la raíz del proyecto para construir y levantar todos los servicios:
   ```bash
   docker compose up --build -d
   ```

3. **Verificar los Servicios**
   - **Frontend/Monolito Django:** Navega a `http://localhost/` (Nginx redirigirá automáticamente a Django).
   - **Healthcheck Nginx:** `http://localhost/health` (confirma que Nginx responde).
   - **Healthcheck Django (real):** `http://localhost/api/health/` — valida que Django puede hablar con la base de datos y con Redis, no solo que el proceso está arriba.
   - **Endpoint Microservicio Flask (pagos):** `http://localhost/api/v2/payments`
   - **Disparar Tarea Asíncrona:** `POST http://localhost/api/trigger-task`

4. **Traducciones (i18n)**
   La internacionalización ya está configurada. Puedes cambiar entre Español (ES) e Inglés (EN) usando el selector de idioma en la parte superior derecha de la interfaz web.

## Arquitectura

- **Nginx (API Gateway):** Puerto `80`. Redirige `/api/v1/` y `/` a Django, y rutas específicas como `/api/v2/payments` a microservicios Flask.
- **Django:** Puerto interno `8000`. Maneja lógica central, UI principal, y consumo de APIs de terceros (Patrón Adapter).
- **Flask (Microservicios):** Servicios desacoplados como `geo-service`, `payment-service`, `auth-service`, `market-service`, etc.
- **RabbitMQ:** Broker de mensajes para microservicios.
- **Redis & Celery:** Cola de tareas asíncronas para Django.

Cada app del monolito Django (`accounts`, `market`, `delivery`, `geo`, `notifications`, `payments`) sigue Clean Architecture con dependencias apuntando hacia adentro:

```
<app>/
├── domain/            # entidades y reglas de negocio, sin dependencias de Django/DRF
├── application/        # use cases: orquestan domain + repositorios
│   └── use_cases/
├── infrastructure/     # implementaciones concretas (modelos ORM, repos, adapters externos)
└── interfaces/          # capa HTTP: vistas DRF, serializers, urls
    ├── api/
    └── serializers/
```

`transactions` es la excepción justificada: es un ledger interno sin API HTTP propia (se invoca directo desde otras apps), así que no tiene `application/` ni `interfaces/`. `common/` agrupa infraestructura cross-cutting (logging, HTTP seguro, middleware) que no pertenece a ningún módulo de negocio.

Ver [Arquitectura](../../wiki/Arquitectura) en la wiki para el detalle completo, incluida la migración a microservicios (Strangler Pattern).

**Estado real de la migración (2026-08-18):** `payment`, `auth`, `market`, `support` y `notifications`/`geo` tienen microservicio Flask propio, pero solo `payment` está integrado de punta a punta. `geo_microservice` y `notifications_microservice` existen, están testeados y corren en `/api/v2/*`/`/api/v3/*`, pero **nada los llama todavía** — el monolito sigue resolviendo `geo`/`notifications` internamente (con Google Maps Platform, no con Nominatim, que es lo que usa la copia del microservicio). Es una decisión de scope deliberada, no trabajo olvidado: integrarlos hoy exigiría primero migrar el geocodificador del microservicio a Google Maps y diseñar una migración de datos para `notifications` (tiene su propia tabla Postgres, separada de la del monolito). Detalle completo en `ROADMAP.local.md`.

## Pruebas

```bash
python manage.py test          # 300+ tests del monolito
ruff check .                   # lint
python manage.py spectacular --validate   # valida el schema OpenAPI
```

Cada microservicio Flask tiene su propia suite (`pytest`) dentro de su carpeta — ver `.github/workflows/ci.yml` para el detalle de la matriz de CI.

## Documentación de la API

El monolito Django expone un spec OpenAPI real generado con `drf-spectacular`:

- **Swagger UI (interactivo):** `http://localhost/api/docs/`
- **Redoc:** `http://localhost/api/redoc/`
- **Schema crudo (YAML):** `http://localhost/api/schema/`

Los microservicios Flask (`/api/v2/`, `/api/v3/`) todavía no tienen spec OpenAPI propio.

## Backups

El monolito (Postgres) y los 5 microservicios con persistencia propia (SQLite) — más `media/` — se pueden respaldar en caliente, sin parar el stack:

```bash
./scripts/backup.sh                # backups/<timestamp>/postgres_cucu.sql.gz + media.tar.gz
./scripts/restore.sh <backup_dir>  # restaura la base compartida completa, con confirmación explícita
```

`backup.sh` usa `pg_dump --clean` sobre la base de Postgres compartida (monolito + el schema propio de cada microservicio: auth, payment, notifications, support, market), guarda un directorio timestamped por corrida, y retiene los últimos 14 días. `geo-service` no tiene base de datos propia. Ver el header de cada script para el detalle y la línea de crontab sugerida para automatizarlo en producción.

## Pruebas de APIs con cURL

**1. Probar un Endpoint JSON propio del sistema**
```bash
curl -X GET http://localhost/api/publicaciones
```

**2. Probar Tarea Asíncrona (Celery)**
```bash
curl -X POST http://localhost/api/trigger-task -H "Content-Type: application/json" -d '{"email":"admin@cucu.local"}'
```

**3. Logs de Celery Worker (Para ver ejecución de tarea asíncrona)**
```bash
docker compose logs -f celery-worker
```

Para instrucciones sobre el despliegue en la nube, revisa [README_DEPLOY_AWS.md](./README_DEPLOY_AWS.md).
Para la revisión de cumplimiento de requisitos, revisa [Entregable2](../../wiki/Entregable2).

## Más información

- [CHANGELOG.md](CHANGELOG.md) — historial de lo que ya se envió.
- [CONTRIBUTING.md](CONTRIBUTING.md) — cómo levantar el entorno y qué revisar antes de un PR.
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — normas de convivencia en el proyecto.
- [SECURITY.md](SECURITY.md) — cómo reportar una vulnerabilidad.
- [DESIGN.md](DESIGN.md) — sistema de diseño (colores, tipografía, componentes).

## Colaboradores

Proyecto desarrollado en equipo:

- [Laura Indaburu](https://github.com/Lauraindabur)
- [Athina Cappelletti](https://github.com/Athina7-7)
- [Tomas Posada](https://github.com/TomasPosada0626)

## Licencia

Copyright 2026 Tomas Posada Suarez.

Este repositorio (el fork activo mantenido desde [@TomasPosada0626](https://github.com/TomasPosada0626)) está licenciado bajo Apache License 2.0 — ver [LICENSE](LICENSE) para el texto completo.
