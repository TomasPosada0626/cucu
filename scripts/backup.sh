#!/usr/bin/env bash
set -euo pipefail

# Backs up the monolith's Postgres database, every microservice's SQLite
# database, and user-uploaded media, all while the stack stays live.
# Postgres uses pg_dump (a consistent snapshot without an offline step);
# the SQLite services use SQLite's own online .backup API instead of `cp`
# - `cp` on an open database can copy a mid-write, corrupt snapshot.
#
# geo-service has no database of its own (see Arquitectura wiki page) so
# it's not included.
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

backup_sqlite() {
  local service="$1" db_path="$2" out_name="$3"
  docker compose exec -T "$service" python3 -c "
import sqlite3
src = sqlite3.connect('$db_path')
dst = sqlite3.connect('/tmp/$out_name')
src.backup(dst)
dst.close()
src.close()
"
  docker compose cp "$service:/tmp/$out_name" "$BACKUP_DIR/$out_name"
  docker compose exec -T "$service" rm -f "/tmp/$out_name"
  log "  $out_name ($(du -h "$BACKUP_DIR/$out_name" | cut -f1))"
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

# Monolith: Postgres now, not SQLite - pg_dump takes a consistent snapshot
# without needing an offline copy step (same "safe against a live DB" property
# .backup() gave us before).
backup_postgres
backup_sqlite payment-service     /app/data/payments.db      payments.db
backup_sqlite notifications-service /app/data/notifications.db notifications.db
backup_sqlite auth-service        /app/data/auth.db          auth.db
backup_sqlite market-service      /app/data/market.db        market.db
backup_sqlite support-service     /app/data/support.db       support.db

# Media (user-uploaded images) - not a database, just archive the directory.
docker compose exec -T django tar czf /tmp/media.tar.gz -C /app media
docker compose cp django:/tmp/media.tar.gz "$BACKUP_DIR/media.tar.gz"
docker compose exec -T django rm -f /tmp/media.tar.gz
log "  media.tar.gz ($(du -h "$BACKUP_DIR/media.tar.gz" | cut -f1))"

log "Backup complete: $BACKUP_DIR ($(du -sh "$BACKUP_DIR" | cut -f1) total)"

# Retention: drop backup directories older than RETENTION_DAYS.
find backups -maxdepth 1 -type d -name "20*" -mtime "+$RETENTION_DAYS" -exec rm -rf {} \;
log "Done. $(find backups -maxdepth 1 -type d -name '20*' | wc -l) backup(s) retained (${RETENTION_DAYS}-day retention)."
