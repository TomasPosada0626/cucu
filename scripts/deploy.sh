#!/usr/bin/env bash
set -euo pipefail

# Pulls the latest main, rebuilds, migrates the database, redeploys, and
# verifies the deploy with a real health check - not just "the containers
# started". If the health check never passes, rolls back to the commit that
# was running before this deploy automatically, no manual intervention
# needed.
#
# Usage (run from the repo root on the EC2 host):
#   ./scripts/deploy.sh

cd "$(dirname "$0")/.."

DEPLOY_LOG=".deploy_history"
HEALTH_URL="http://localhost/api/health/"
MAX_HEALTH_CHECKS=15
HEALTH_CHECK_INTERVAL=4

log() {
  echo "[$(date -Iseconds)] $*"
}

PREV_SHA=$(git rev-parse HEAD)
log "Current commit: $PREV_SHA"

git pull
NEW_SHA=$(git rev-parse HEAD)

if [ "$PREV_SHA" = "$NEW_SHA" ]; then
  log "Already up to date, nothing to deploy."
  exit 0
fi

log "Deploying $NEW_SHA (was $PREV_SHA)"

# --build is not optional - see README_DEPLOY_AWS.md section 6 for why a
# plain `up -d` after a requirements.txt change crash-loops the containers.
docker compose up -d --build

log "Applying database migrations..."
docker compose exec -T django python manage.py migrate --noinput

docker compose restart nginx

log "Waiting for /api/health/ to report healthy..."
for i in $(seq 1 "$MAX_HEALTH_CHECKS"); do
  if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    log "Deploy succeeded: $NEW_SHA is live and healthy."
    echo "$(date -Iseconds) $PREV_SHA $NEW_SHA ok" >> "$DEPLOY_LOG"
    exit 0
  fi
  sleep "$HEALTH_CHECK_INTERVAL"
done

log "Health check never passed after $((MAX_HEALTH_CHECKS * HEALTH_CHECK_INTERVAL))s. Rolling back to $PREV_SHA automatically."
echo "$(date -Iseconds) $PREV_SHA $NEW_SHA failed-rolled-back" >> "$DEPLOY_LOG"
"$(dirname "$0")/rollback.sh" --auto "$PREV_SHA"
exit 1
