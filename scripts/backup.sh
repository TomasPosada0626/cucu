#!/usr/bin/env bash
set -euo pipefail

# Backs up the shared Postgres database (monolith + every microservice's
# own schema) and user-uploaded media, all while the stack stays live.
# pg_dump takes a consistent snapshot without needing an offline step.
#
# geo-service has no database of its own (see Arquitectura wiki page).
# Every other microservice - auth, payment, notifications, support, and
# market - has moved off SQLite onto its own schema in this same Postgres
# instance (see Migracion-a-Microservicios wiki page), so one pg_dump
# covers all of them; there's no more SQLite-specific backup step.
#
# Usage (run from the repo root, with `docker compose up -d` already running):
#   ./scripts/backup.sh
#
# Install as a daily cron job - see README section this script is linked
# from for the exact crontab line.

cd "$(dirname "$0")/.."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$TIMESTAMP"
RETENTION_DAYS=14

mkdir -p "$BACKUP_DIR"

log() {
  echo "[$(date -Iseconds)] $*"
}

backup_postgres() {
  local out_name="postgres_cucu.sql.gz"
  # --clean --if-exists: the dump includes DROP-IF-EXISTS before each CREATE,
  # so restore.sh can pipe it straight into psql without a manual drop step.
  docker compose exec -T postgres sh -c \
    'pg_dump --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip' > "$BACKUP_DIR/$out_name"
  log "  $out_name ($(du -h "$BACKUP_DIR/$out_name" | cut -f1))"
}

log "Starting backup to $BACKUP_DIR"

backup_postgres

# Media (user-uploaded images) - not a database, just archive the directory.
docker compose exec -T django tar czf /tmp/media.tar.gz -C /app media
docker compose cp django:/tmp/media.tar.gz "$BACKUP_DIR/media.tar.gz"
docker compose exec -T django rm -f /tmp/media.tar.gz
log "  media.tar.gz ($(du -h "$BACKUP_DIR/media.tar.gz" | cut -f1))"

log "Backup complete: $BACKUP_DIR ($(du -sh "$BACKUP_DIR" | cut -f1) total)"

# Retention: drop backup directories older than RETENTION_DAYS.
find backups -maxdepth 1 -type d -name "20*" -mtime "+$RETENTION_DAYS" -exec rm -rf {} \;
log "Done. $(find backups -maxdepth 1 -type d -name '20*' | wc -l) backup(s) retained (${RETENTION_DAYS}-day retention)."
