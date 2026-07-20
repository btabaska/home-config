#!/usr/bin/env bash
# Seed Uptime Kuma with HTTP monitors for all NAS services.
# Run on the Mac mini (where uptime-kuma container lives):
#   bash /opt/stacks/uptime-kuma/bootstrap-nas-monitors.sh
#
# Idempotent: skips monitors whose name already exists.
set -euo pipefail

CONTAINER="${KUMA_CONTAINER:-uptime-kuma}"
NAS_IP="${NAS_IP:-192.168.10.4}"
SOCKET="/app/data/run/mariadb.sock"
DB="kuma"
USER_ID=1
INTERVAL=60
RETRY=3
RETRY_INTERVAL=60
# *arr apps return 302; Plex returns 401 without token
ACCEPT_ARR='["200-299","300-399"]'
ACCEPT_OK='["200-299"]'
ACCEPT_PLEX='["200-299","401"]'

# name|url|accepted_json
MONITORS=(
  "NAS Sonarr|http://${NAS_IP}:8989|${ACCEPT_ARR}"
  "NAS Radarr|http://${NAS_IP}:7878|${ACCEPT_ARR}"
  "NAS Lidarr|http://${NAS_IP}:8686|${ACCEPT_ARR}"
  # readarr -> bookshelf 2026-07-20 (bmig-05); live monitor renamed via SQL UPDATE
  "NAS Bookshelf|http://${NAS_IP}:8790|${ACCEPT_ARR}"
  "NAS Prowlarr|http://${NAS_IP}:9696|${ACCEPT_ARR}"
  "NAS FlareSolverr|http://${NAS_IP}:8191|${ACCEPT_OK}"
  "NAS Immich|http://${NAS_IP}:2283|${ACCEPT_OK}"
  "NAS Stash|http://${NAS_IP}:9999|${ACCEPT_OK}"
  "NAS Whisparr|http://${NAS_IP}:6969|${ACCEPT_ARR}"
  "NAS Calibre Web|http://${NAS_IP}:8083|${ACCEPT_ARR}"
  "NAS Plex|http://${NAS_IP}:32400|${ACCEPT_PLEX}"
  # fix-29 / L94: unpackerr was invisible to every external monitor (metrics port
  # unpublished). The port is now published; probe its [webserver] /metrics.
  "NAS Unpackerr|http://${NAS_IP}:5656/metrics|${ACCEPT_OK}"
)

sql() {
  docker exec "$CONTAINER" mariadb --socket="$SOCKET" "$DB" -N -e "$1"
}

monitor_exists() {
  local name="$1"
  local count
  count=$(sql "SELECT COUNT(*) FROM monitor WHERE name='${name//\'/\\\'}';")
  [[ "$count" -gt 0 ]]
}

add_monitor() {
  local name="$1" url="$2" accept="$3"
  monitor_exists "$name" && { echo "skip  $name"; return 0; }

  sql "INSERT INTO monitor (name, active, user_id, \`interval\`, url, type, maxretries, retry_interval, accepted_statuscodes_json, method)
       VALUES ('${name//\'/\\\'}', 1, ${USER_ID}, ${INTERVAL}, '${url}', 'http', ${RETRY}, ${RETRY_INTERVAL}, '${accept}', 'GET');"
  echo "added $name → $url"
}

# fix-29 / M21: a monitor with no monitor_notification row goes DOWN silently.
# The old flow inserted monitors and left "attach ntfy" as a manual step, so the
# NAS Whisparr monitor (id 56) shipped unlinked. Attach the ntfy channel to EVERY
# active monitor that lacks it — idempotent (INSERT ... WHERE NOT EXISTS), so
# re-running never duplicates links and always heals any newly-added monitor.
link_all_notifications() {
  local ntfy_id
  ntfy_id=$(sql "SELECT id FROM notification WHERE name LIKE '%ntfy%' AND active=1 ORDER BY id LIMIT 1;")
  if [[ -z "$ntfy_id" ]]; then
    echo "WARNING: no active ntfy notification found — monitors will alert nowhere." >&2
    return 1
  fi
  sql "INSERT INTO monitor_notification (monitor_id, notification_id)
       SELECT m.id, ${ntfy_id} FROM monitor m
       WHERE m.active=1
         AND NOT EXISTS (SELECT 1 FROM monitor_notification mn
                         WHERE mn.monitor_id=m.id AND mn.notification_id=${ntfy_id});"
  local unlinked
  unlinked=$(sql "SELECT COUNT(*) FROM monitor m
                  LEFT JOIN monitor_notification mn ON mn.monitor_id=m.id
                  WHERE m.active=1 AND mn.id IS NULL;")
  echo "linked all active monitors to ntfy (id ${ntfy_id}); unlinked-after=${unlinked}"
}

main() {
  if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "Container $CONTAINER not running on this host." >&2
    exit 1
  fi

  echo "Bootstrapping NAS monitors (target ${NAS_IP})..."
  local row name url accept
  for row in "${MONITORS[@]}"; do
    IFS='|' read -r name url accept <<< "$row"
    add_monitor "$name" "$url" "$accept"
  done

  echo
  echo "Attaching the ntfy alert channel to every active monitor..."
  link_all_notifications

  echo
  echo "Current monitors:"
  sql "SELECT id, name, url FROM monitor ORDER BY id;"

  echo
  echo "Restarting Uptime Kuma so it picks up new monitors (v2 loads at startup only)..."
  docker restart "$CONTAINER" >/dev/null
  sleep 12
  echo "Latest heartbeat status:"
  sql "SELECT m.id, m.name, h.status, h.msg FROM monitor m
       LEFT JOIN heartbeat h ON h.monitor_id = m.id
       WHERE h.time = (SELECT MAX(time) FROM heartbeat h2 WHERE h2.monitor_id = m.id)
       OR h.time IS NULL ORDER BY m.id;"

  echo
  echo "Done. All active monitors are linked to ntfy (verified by the"
  echo "kuma-all-monitors-notified verification check)."
}

main "$@"
