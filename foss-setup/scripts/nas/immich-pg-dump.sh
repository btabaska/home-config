#!/usr/bin/env bash
# Nightly Immich Postgres dump for Hyper Backup (nas-08 follow-up).
# Schedule in DSM Task Scheduler: root, daily ~02:30, run:
#   /volume1/docker/immich/immich-pg-dump.sh
set -euo pipefail

BACKUP_DIR="/volume1/docker/immich/backups"
STAMP="$(date +%F)"
OUT="${BACKUP_DIR}/immich-${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"
docker exec -t immich_postgres pg_dumpall --clean --if-exists -U postgres | gzip > "${OUT}"
find "${BACKUP_DIR}" -name 'immich-*.sql.gz' -mtime +14 -delete
