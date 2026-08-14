# CUCU — Comida casera en cocas cerca de ti

<img width="1191" height="707" alt="image" src="https://github.com/user-attachments/assets/dc99b69f-c6b5-45a6-9abd-fae4f4a72edf" />

CUCU es un marketplace local de comida casera: conecta a personas que tienen porciones adicionales de comida ("cocas") con usuarios cercanos que buscan una alternativa rápida, económica y casera para alimentarse. La ubicación geográfica es el eje del producto: publicaciones, notificaciones y cierre de la transacción dependen de la cercanía entre comprador y vendedor.

El proyecto está construido con un modelo híbrido: **Django (monolito para vistas y lógica central) + Flask (microservicios especializados)**, con **RabbitMQ** y **Redis** como servicios de apoyo. Todo se orquesta con **Docker Compose** y se expone a través de un **API Gateway (Nginx)**.

Más contexto de negocio y las entregas académicas del proyecto están en la [Wiki](../../wiki).

## Estado del proyecto

Este repo es un fork activo mantenido por [@TomasPosada0626](https://github.com/TomasPosada0626) a partir del trabajo original en equipo. Hay una hoja de ruta de mejoras en curso — ver los [Issues](../../issues) para el detalle y prioridad de cada frente (seguridad, arquitectura limpia, tests, microservicios).

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
   - **Healthcheck Nginx:** `http://localhost/health`
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
