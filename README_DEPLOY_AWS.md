# Despliegue en AWS EC2 - Proyecto CUCU

Esta guía describe los pasos necesarios para desplegar el proyecto CUCU (Django + Flask + RabbitMQ + Redis + Celery + Nginx) en una instancia **Amazon EC2** basada en Ubuntu/Linux.

## 1. Lanzar Instancia EC2

1. Ve a la consola de AWS EC2 y selecciona **Launch Instance**.
2. Elige la AMI **Ubuntu Server 24.04 LTS**.
3. Selecciona el tipo de instancia (recomendado `t3.medium` o superior debido a la cantidad de contenedores, o mínimo `t2.micro` con archivo Swap configurado).
4. Crea o usa un **Key Pair** para conectar por SSH.
5. En **Network Settings**, permite tráfico SSH (22), HTTP (80) y HTTPS (443).
6. Lanza la instancia.

## 2. Configurar Servidor e Instalar Docker

Conéctate por SSH:
```bash
ssh -i "tu-llave.pem" ubuntu@IP_PUBLICA_EC2
```

Actualiza el sistema e instala Docker y Docker Compose:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-v2 git

# Agrega tu usuario al grupo docker
sudo usermod -aG docker $USER
newgrp docker
```

*(Opcional en t2.micro) Configurar Swap de 2GB si falta memoria para los builds:*
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 3. Clonar el Proyecto y Configurar Variables

Clona tu repositorio:
```bash
git clone https://github.com/tu-usuario/cucu.git
cd cucu
```

Crea el archivo `.env` basado en la plantilla:
```bash
cp .env.example .env
nano .env
```
Ajusta la variable `ALLOWED_HOSTS` en `.env` para incluir la IP pública de tu EC2 o tu dominio:
```env
ALLOWED_HOSTS=localhost,127.0.0.1,IP_PUBLICA_EC2,tu-dominio.com
```

## 4. Desplegar los Contenedores

Levanta el ecosistema completo:
```bash
docker compose up --build -d
```

Verifica que todos los contenedores estén corriendo (`Up`):
```bash
docker compose ps
```

Si hay algún error, revisa los logs:
```bash
docker compose logs -f [nombre-servicio]
```

## 5. Acceder a la Aplicación

Abre tu navegador y ve a la IP pública o dominio apuntado a tu instancia:
```text
http://IP_PUBLICA_EC2/
```
Nginx como API Gateway se encargará de enrutar las solicitudes HTTP al monolito de Django y a los microservicios Flask según las reglas definidas en `nginx.conf`.

## 6. Actualizar el Despliegue

**Recomendado:** `./scripts/deploy.sh` hace exactamente los pasos de abajo, corre `manage.py migrate` automáticamente (para que una migración nueva - como un índice - no se quede sin aplicar en silencio), y además espera a que `/api/health/` responda de verdad antes de darse por exitoso; si nunca responde, hace rollback automático al commit anterior sin que nadie tenga que darse cuenta a mano. Ver `scripts/deploy.sh` y `scripts/rollback.sh` para el detalle — verificados en vivo, no solo escritos.

Paso a paso manual, para entender qué hace o si preferís correrlo vos mismo:

```bash
git pull
docker compose up -d --build
docker compose exec -T django python manage.py migrate --noinput
```

**`--build` no es opcional.** Sin esa flag, `docker compose up -d` recrea los contenedores reusando la imagen vieja — si el `git pull` trajo un cambio en `requirements.txt` (una dependencia nueva), el contenedor arranca con el código nuevo pero las librerías viejas y crashea en loop con `ModuleNotFoundError`. Esto no es teórico: pasó exactamente así probando `drf-spectacular` en local. Verificado en vivo: `docker compose up -d` (sin `--build`) tumbó `django` y `celery-worker` con ese error; `docker compose up -d --build` los arregló.

**Si algún servicio backend se recreó** (verificalo con `docker compose ps` — el campo `CREATED` te dice cuáles), reiniciá nginx después:

```bash
docker compose restart nginx
```

Nginx resuelve la IP interna de cada servicio (`django`, `payment-service`, etc.) una sola vez al arrancar. Si ese servicio se recrea, su IP interna cambia y nginx sigue apuntando a la IP vieja hasta que se reinicia — el síntoma es un 502 Bad Gateway aunque `docker compose ps` diga que el servicio está `healthy`. También verificado en vivo con el mismo escenario de arriba.

Después de actualizar, confirmá que todo levantó bien:
```bash
docker compose ps
curl -f http://localhost/api/health/   # valida DB + Redis del monolito, no solo que el proceso responda
```

## 7. Migrar el monolito de SQLite a Postgres (una sola vez)

Si tu instancia ya está corriendo desde antes de que el monolito pasara a Postgres, `db.sqlite3` tiene datos reales que hay que llevar — esto no es un `git pull` normal. Verificado paso a paso en local antes de escribir esto.

**Antes de tocar nada**, respaldá lo que hay:
```bash
cp db.sqlite3 db.sqlite3.pre-postgres-backup
```

**1. Con el código todavía en la versión vieja (antes del pull), exportá los datos.** Tiene que ser con la app *apuntando a SQLite todavía* — si ya hiciste `git pull`, hacé `git stash` de `config/settings.py` primero para volver a apuntarla ahí temporalmente:
```bash
docker compose exec -T -e PYTHONUTF8=1 django python manage.py dumpdata \
  --natural-foreign --natural-primary \
  --exclude admin.logentry --exclude contenttypes --exclude auth.permission --exclude sessions.session \
  --indent 2 -o /app/pre_postgres_data.json
```
`PYTHONUTF8=1` no es opcional: sin forzar UTF-8, el volcado puede corromper tildes y eñes silenciosamente (pasó en Windows probando esto — el archivo parecía válido hasta que `loaddata` tiraba `UnicodeDecodeError`).

**2. Traé el código nuevo y agregá las variables de Postgres a `.env`:**
```bash
git stash pop 2>/dev/null || true   # si hiciste stash en el paso 1
git pull
```
Agregá a `.env` (ver `.env.example`):
```env
POSTGRES_DB=cucu
POSTGRES_USER=cucu
POSTGRES_PASSWORD=algo-que-no-sea-el-placeholder
```

**3. Levantá Postgres y reconstruí las imágenes** (nueva dependencia en `requirements.txt`, ver sección 6):
```bash
docker compose up -d --build
```

**4. Corré las migraciones contra la base nueva, vacía, y cargá los datos:**
```bash
docker compose exec -T django python manage.py migrate
docker compose exec -T django python manage.py loaddata pre_postgres_data.json
```

**5. Verificá antes de dar por cerrada la migración:**
```bash
docker compose restart nginx   # el django que reconstruiste tiene una IP interna nueva
curl -f http://localhost/api/health/
docker compose exec -T django python manage.py shell -c \
  "from accounts.infrastructure.models import User; print(User.objects.count())"
```
Compará ese número de usuarios con lo que esperabas antes de la migración. Si coincide y el healthcheck da 200, guardá `db.sqlite3.pre-postgres-backup` en un lugar seguro fuera del servidor (no lo necesitás para que la app funcione, pero es tu única copia de los datos viejos si algo salió mal) y seguí con el flujo normal de backups (`scripts/backup.sh`, sección de Backups en el README principal).
