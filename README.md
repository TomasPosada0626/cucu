# CUCU Comida casera en cocas cerca de ti
<img width="1191" height="707" alt="image" src="https://github.com/user-attachments/assets/dc99b69f-c6b5-45a6-9abd-fae4f4a72edf" />

Este proyecto es una plataforma construida con un modelo híbrido: **Django (Monolito para vistas y lógica central) + Flask (Microservicios especializados)** y servicios de apoyo como RabbitMQ y Redis. Todo orquestado con **Docker Compose** y expuesto a través de un **API Gateway (Nginx)**.


## Dirección ip elástica:   [cucu](http://98.90.207.183/)
http://98.90.207.183/


## Requisitos Previos

- Docker y Docker Compose instalados.
- Clonar este repositorio.

## Ejecución Local con Docker Compose

1. **Configurar Variables de Entorno**
   Copia el archivo de ejemplo para crear tus variables locales:
   ```bash
   cp .env.example .env
   ```

2. **Levantar el Ecosistema**
   Ejecuta el siguiente comando en la raíz del proyecto para construir y levantar todos los servicios:
   ```bash
-   docker compose up --build -d
   ```

3. **Verificar los Servicios**
   - **Frontend/Monolito Django:** Navega a `http://localhost/` (Nginx redirigirá automáticamente a Django).
   - **Healthcheck Nginx:** `http://localhost/health`
   - **Endpoint Microservicio Flask (pagos):** `http://localhost/api/v2/payments`
   - **Endpoint Terceros/Aliados:** `http://localhost/api/external-services`
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

**2. Probar consumo de APIs Terceros y Servicio Aliado (Patrón Adapter)**
```bash
curl -X GET http://localhost/api/external-services?email=usuario@ejemplo.com
```

**3. Probar Tarea Asíncrona (Celery)**
```bash
curl -X POST http://localhost/api/trigger-task -H "Content-Type: application/json" -d '{"email":"admin@cucu.local"}'
```

**4. Logs de Celery Worker (Para ver ejecución de tarea asíncrona)**
```bash
docker compose logs -f celery-worker
```

Para instrucciones sobre el despliegue en la nube, revisa [README_DEPLOY_AWS.md](./README_DEPLOY_AWS.md).
Para la revisión de cumplimiento de requisitos, revisa [Entregable2](../../wiki/Entregable2).
