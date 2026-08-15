#!/usr/bin/env bash
set -euo pipefail

# Rolls the deployed code back to a previous commit, rebuilds, redeploys, and
# verifies with the same health check deploy.sh uses. DESTRUCTIVE to the
# working tree on this checkout (git reset --hard) - this script's only job
# is to be the deploy checkout on the server, so that's the intended use;
# never run it against a clone you're actively developing on.
#
# Usage:
#   ./scripts/rollback.sh                 # rolls back to the last known-good commit in .deploy_history
#   ./scripts/rollback.sh <git-sha>       # rolls back to a specific commit
#
# --auto is used internally by deploy.sh when a fresh deploy fails its own
# health check - skips the confirmation prompt since it's an automated
# response to a failed deploy, not a manual decision.

cd "$(dirname "$0")/.."

DEPLOY_LOG=".deploy_history"
HEALTH_URL="http://localhost/api/health/"
MAX_HEALTH_CHECKS=15
HEALTH_CHECK_INTERVAL=4
AUTO=false

if [ "${1:-}" = "--auto" ]; then
  AUTO=true
  shift
fi

TARGET_SHA="${1:-}"

if [ -z "$TARGET_SHA" ]; then
  # Last "ok" entry in the deploy log - the last commit that actually passed
  # its health check, not just the last one attempted.
  TARGET_SHA=$(grep ' ok$' "$DEPLOY_LOG" 2>/dev/null | tail -1 | awk '{print $2}')
  if [ -z "$TARGET_SHA" ]; then
    echo "No target commit given and no successful deploy found in $DEPLOY_LOG." >&2
    echo "Usage: $0 [--auto] <git-sha>" >&2
    exit 1
  fi
  echo "No commit given - using the last known-good deploy: $TARGET_SHA"
fi

log() {
  echo "[$(date -Iseconds)] $*"
}

if [ "$AUTO" = false ]; then
  echo "This will reset the working tree to $TARGET_SHA and redeploy."
  echo "Any local changes on this checkout not yet committed will be lost."
  echo
  read -rp "Type 'rollback' to confirm: " CONFIRM
  if [ "$CONFIRM" != "rollback" ]; then
    echo "Confirmation did not match. Aborted."
    exit 1
  fi
fi

log "Rolling back to $TARGET_SHA"
git fetch origin
git reset --hard "$TARGET_SHA"

docker compose up -d --build

log "Applying database migrations..."
docker compose exec -T django python manage.py migrate --noinput

# See deploy.sh for why this must be --force-recreate, not restart: nginx.conf
# is a single-file bind mount, and `git reset --hard` replaces it via rename
# (a new inode) that a plain restart won't pick up on Linux Docker.
docker compose up -d --force-recreate nginx

log "Waiting for /api/health/ to report healthy..."
for i in $(seq 1 "$MAX_HEALTH_CHECKS"); do
  if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    log "Rollback succeeded: $TARGET_SHA is live and healthy."
    echo "$(date -Iseconds) rollback -> $TARGET_SHA ok" >> "$DEPLOY_LOG"
    exit 0
  fi
  sleep "$HEALTH_CHECK_INTERVAL"
done

log "Health check never passed after rolling back to $TARGET_SHA either."
log "This needs a human - the last two commits are both unhealthy, or something else broke (DB, Redis, RabbitMQ, disk)."
echo "$(date -Iseconds) rollback -> $TARGET_SHA still-unhealthy" >> "$DEPLOY_LOG"
exit 1
