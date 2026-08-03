#!/usr/bin/env bash
# DEPRECATED — superseded by immich-db-dump.sh, which is the script DSM task 9
# actually runs (see install-immich-dump-task.sh). Kept only for provenance.
# It lacks the small-dump guard, full docker path, and healthchecks ping; do not
# schedule it. Retention aligned to KEEP_DAYS=7 (fix-60/SL29) to avoid a
# misleading 14-vs-7 discrepancy in the repo.
set -euo pipefail

BACKUP_DIR="/volume1/docker/immich/backups"
STAMP="$(date +%F)"
OUT="${BACKUP_DIR}/immich-${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"
docker exec -t immich_postgres pg_dumpall --clean --if-exists -U postgres | gzip > "${OUT}"
find "${BACKUP_DIR}" -name 'immich-*.sql.gz' -mtime +7 -delete
