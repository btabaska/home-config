#!/usr/bin/env bash
# Nightly Immich Postgres dump (DSM Task Scheduler, 02:30) + Healthchecks ping.
# DSM rewrites /etc/crontab, so this must ONLY be scheduled as a DSM task —
# never as a raw crontab line (that's how the 2026-07-07 schedule got lost).
set -euo pipefail
DOCKER=/usr/local/bin/docker
OUT_DIR=/volume1/docker/immich/backups
KEEP_DAYS=14
PING_URL="http://192.168.10.2:8001/ping/df506ce5-202d-4012-a35c-182809d3b77a"

out="${OUT_DIR}/immich-$(date +%F).sql.gz"
tmp="${out}.tmp"
"$DOCKER" exec immich_postgres pg_dumpall --clean --if-exists -U postgres | gzip > "$tmp"
# refuse suspiciously small dumps (schema-only ~ <1MB; last good ~17MB)
[ "$(stat -c%s "$tmp")" -gt 1000000 ] || { echo "dump too small: $(stat -c%s "$tmp") bytes" >&2; rm -f "$tmp"; exit 1; }
mv "$tmp" "$out"
find "$OUT_DIR" -name 'immich-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
curl -fsS -m 10 --retry 3 -o /dev/null "$PING_URL" || echo "WARN: healthchecks ping failed" >&2
echo "OK: $out ($(stat -c%s "$out") bytes)"
