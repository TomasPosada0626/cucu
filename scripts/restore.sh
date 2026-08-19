#!/usr/bin/env bash
set -euo pipefail

# Restores the shared Postgres database from a backup produced by backup.sh.
# DESTRUCTIVE: stops every service that reads/writes this database, replaces
# every table (monolith + every microservice's own schema) in one shot,
# restarts them. Any writes made after that backup was taken are lost -
# that's the point of a restore, but it means this needs a typed
# confirmation, not just -y.
#
# Usage: ./scripts/restore.sh <backup_dir>
#   e.g. ./scripts/restore.sh backups/20260815_030000
#
# geo-service has no database of its own, so it isn't in this list - there's
# nothing on it a Postgres restore would affect.
SERVICES="django celery-worker auth-service payment-service notifications-service notifications-worker support-service market-service"

cd "$(dirname "$0")/.."

BACKUP_DIR="${1:-}"

if [ -z "$BACKUP_DIR" ]; then
  echo "Usage: $0 <backup_dir>" >&2
  echo "  e.g. $0 backups/20260815_030000" >&2
  exit 1
fi

SRC="$BACKUP_DIR/postgres_cucu.sql.gz"
if [ ! -f "$SRC" ]; then
  echo "Backup file not found: $SRC" >&2
  exit 1
fi

echo "This will REPLACE every table in the shared Postgres database with:"
echo "  $SRC"
echo "That's the monolith plus every microservice's own schema (auth, payment,"
echo "notifications, support, market)."
echo "These services will be stopped during the restore, then restarted: $SERVICES"
echo "Any data written after this backup was taken will be lost."
echo
read -rp "Type 'restore' to confirm: " CONFIRM
if [ "$CONFIRM" != "restore" ]; then
  echo "Confirmation did not match. Aborted."
  exit 1
fi

# shellcheck disable=SC2086
docker compose stop $SERVICES
gunzip -c "$SRC" | docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
# shellcheck disable=SC2086
docker compose start $SERVICES

# nginx caches each upstream's container IP when it starts. django (and the
# microservices) get a new IP on restart, so without this nginx keeps
# routing to the old address and every request 502s until it's restarted -
# confirmed by hand while testing this script. Same root cause as the
# nginx.conf bind-mount quirk documented in README_DEPLOY_AWS.md, different
# trigger (container IP, not config content).
docker compose restart nginx

echo "Restored the shared Postgres database from $SRC and restarted: $SERVICES nginx"
# shellcheck disable=SC2086
echo "Verify everything came back healthy: docker compose ps $SERVICES nginx"
