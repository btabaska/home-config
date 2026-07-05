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
  "NAS Readarr|http://${NAS_IP}:8787|${ACCEPT_ARR}"
  "NAS Prowlarr|http://${NAS_IP}:9696|${ACCEPT_ARR}"
  "NAS FlareSolverr|http://${NAS_IP}:8191|${ACCEPT_OK}"
  "NAS Immich|http://${NAS_IP}:2283|${ACCEPT_OK}"
  "NAS DepTrack|http://${NAS_IP}:9010|${ACCEPT_OK}"
  "NAS Stash|http://${NAS_IP}:9999|${ACCEPT_OK}"
  "NAS Calibre Web|http://${NAS_IP}:8083|${ACCEPT_ARR}"
  "NAS Plex|http://${NAS_IP}:32400|${ACCEPT_PLEX}"
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
  echo "Next: Uptime Kuma → Settings → Notifications → add ntfy webhook,"
  echo "      then attach it to the NAS monitor group."
}

main "$@"
