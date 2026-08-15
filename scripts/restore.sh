#!/usr/bin/env bash
set -euo pipefail

# Restores one service's database from a backup produced by backup.sh.
# DESTRUCTIVE: stops the service, overwrites its live database, restarts it.
# Any writes made after that backup was taken are lost - that's the point
# of a restore, but it means this needs a typed confirmation, not just -y.
#
# Usage: ./scripts/restore.sh <service> <backup_dir>
#   e.g. ./scripts/restore.sh payment-service backups/20260815_030000

cd "$(dirname "$0")/.."

SERVICE="${1:-}"
BACKUP_DIR="${2:-}"

if [ -z "$SERVICE" ] || [ -z "$BACKUP_DIR" ]; then
  echo "Usage: $0 <service> <backup_dir>" >&2
  echo "  services: django (Postgres), payment-service, notifications-service, auth-service, market-service, support-service" >&2
  echo "  e.g. $0 payment-service backups/20260815_030000" >&2
  exit 1
fi

if [ "$SERVICE" = "django" ]; then
  SRC="$BACKUP_DIR/postgres_cucu.sql.gz"
  if [ ! -f "$SRC" ]; then
    echo "Backup file not found: $SRC" >&2
    exit 1
  fi

  echo "This will REPLACE every table in the monolith's Postgres database with:"
  echo "  $SRC"
  echo "django and celery-worker will be stopped during the restore, then restarted."
  echo "Any data written after this backup was taken will be lost."
  echo
  read -rp "Type 'django' to confirm: " CONFIRM
  if [ "$CONFIRM" != "django" ]; then
    echo "Confirmation did not match. Aborted."
    exit 1
  fi

  docker compose stop django celery-worker
  gunzip -c "$SRC" | docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
  docker compose start django celery-worker

  echo "Restored the monolith's Postgres database from $SRC and restarted django + celery-worker."
  echo "Verify it came back healthy: docker compose ps django celery-worker"
  exit 0
fi

case "$SERVICE" in
  payment-service)       DB_PATH=/app/data/payments.db;       DB_FILE=payments.db ;;
  notifications-service) DB_PATH=/app/data/notifications.db;  DB_FILE=notifications.db ;;
  auth-service)          DB_PATH=/app/data/auth.db;           DB_FILE=auth.db ;;
  market-service)        DB_PATH=/app/data/market.db;         DB_FILE=market.db ;;
  support-service)       DB_PATH=/app/data/support.db;        DB_FILE=support.db ;;
  *)
    echo "Unknown service '$SERVICE'." >&2
    echo "  services: django (Postgres), payment-service, notifications-service, auth-service, market-service, support-service" >&2
    exit 1
    ;;
esac

SRC="$BACKUP_DIR/$DB_FILE"
if [ ! -f "$SRC" ]; then
  echo "Backup file not found: $SRC" >&2
  exit 1
fi

echo "This will REPLACE the live database for '$SERVICE' ($DB_PATH) with:"
echo "  $SRC"
echo "The service will be stopped, then restarted after the restore."
echo "Any data written to '$SERVICE' after this backup was taken will be lost."
echo
read -rp "Type the service name to confirm ($SERVICE): " CONFIRM
if [ "$CONFIRM" != "$SERVICE" ]; then
  echo "Confirmation did not match. Aborted."
  exit 1
fi

docker compose stop "$SERVICE"
docker compose cp "$SRC" "$SERVICE:$DB_PATH"
docker compose start "$SERVICE"

echo "Restored $SERVICE from $SRC and restarted the service."
echo "Verify it came back healthy: docker compose ps $SERVICE"
