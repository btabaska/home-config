#!/usr/bin/env bash
# NAS Docker stack health check + auto-recovery.
# Idempotent: safe to run every 15 min from DSM Task Scheduler (root).
#
# Brings up all compose stacks, verifies critical LAN ports, logs results.
# Optional ntfy alert when services stay down after recovery (see health.env).
#
# Install: sudo bash /volume1/scripts/nas/install-nas-docker-health-task.sh
set -uo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

DOCKER="${DOCKER:-/usr/local/bin/docker}"
COMPOSE="${COMPOSE:-/usr/local/bin/docker compose}"
LOG="${LOG:-/var/log/nas-docker-health.log}"
ENV_FILE="${ENV_FILE:-/volume1/scripts/nas/health.env}"
START_SCRIPT="/var/packages/ContainerManager/scripts/start-stop-status"

# name:host:port:acceptable_http_codes (comma-separated, e.g. 200,302,401)
CHECKS=(
  "sonarr:127.0.0.1:8989:200,302"
  "radarr:127.0.0.1:7878:200,302"
  "lidarr:127.0.0.1:8686:200,302"
  "readarr:127.0.0.1:8787:200,302"
  "prowlarr:127.0.0.1:9696:200,302"
  "flaresolverr:127.0.0.1:8191:200"
  "immich:127.0.0.1:2283:200"
  "deptrack:127.0.0.1:9010:200"
  "stash:127.0.0.1:9999:200"
  "cwa:127.0.0.1:8083:200,302"
  "plex:127.0.0.1:32400:200,401"
)

ts() { date -Is; }
log() { printf '[%s] %s\n' "$(ts)" "$*" | tee -a "$LOG"; }

load_env() {
  [[ -f "$ENV_FILE" ]] && set -a && # shellcheck disable=SC1090
    source "$ENV_FILE" && set +a
}

start_container_manager() {
  if [[ -x "$START_SCRIPT" ]]; then
    log "Starting Container Manager..."
    "$START_SCRIPT" start
    return
  fi
  log "Starting Container Manager via synopkg..."
  /usr/syno/bin/synopkg start ContainerManager
}

wait_for_docker() {
  local i
  for i in $(seq 1 30); do
    if "$DOCKER" info >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

compose_up_dir() {
  local dir="$1"
  [[ -d "$dir" ]] || return 0

  if [[ -f "$dir/docker-compose.yml" ]]; then
    log "compose up -d: $dir"
    $COMPOSE -f "$dir/docker-compose.yml" up -d --no-recreate >>"$LOG" 2>&1 \
      || log "WARN: compose up failed for $dir"
    return
  fi

  if [[ -f "$dir/compose.yaml" ]]; then
    local files=(-f "$dir/compose.yaml")
    [[ -f "$dir/compose.nas.yaml" ]] && files+=(-f "$dir/compose.nas.yaml")
    log "compose up -d: $dir"
    $COMPOSE "${files[@]}" up -d --no-recreate >>"$LOG" 2>&1 \
      || log "WARN: compose up failed for $dir"
  fi
}

bring_up_stacks() {
  compose_up_dir /volume1/docker/media-automation
  compose_up_dir /volume1/docker/immich
  compose_up_dir /volume1/docker/stash
  compose_up_dir /volume1/docker/calibre-web-automated
  compose_up_dir /volume1/docker/dependency-track
}

code_ok() {
  local code="$1" allowed="$2"
  local c
  IFS=',' read -ra codes <<< "$allowed"
  for c in "${codes[@]}"; do
    [[ "$code" == "$c" ]] && return 0
  done
  return 1
}

check_port() {
  local name="$1" host="$2" port="$3" allowed="$4"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "http://${host}:${port}/" 2>/dev/null) \
    || code="000"
  if code_ok "$code" "$allowed"; then
    log "OK   $name ($host:$port) HTTP $code"
    return 0
  fi
  log "DOWN $name ($host:$port) HTTP $code (want $allowed)"
  return 1
}

ntfy_alert() {
  local title="$1" message="$2" priority="${3:-4}"
  [[ -n "${NTFY_URL:-}" && -n "${NTFY_TOPIC:-}" ]] || return 0

  local args=(-sS -X POST "${NTFY_URL%/}/${NTFY_TOPIC}")
  [[ -n "${NTFY_TOKEN:-}" ]] && args+=(-H "Authorization: Bearer ${NTFY_TOKEN}")
  args+=(-H "Title: ${title}" -H "Priority: ${priority}" -d "$message")
  curl "${args[@]}" >/dev/null 2>&1 || log "WARN: ntfy publish failed"
}

main() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Run as root: sudo bash $0" >&2
    exit 1
  fi

  load_env
  log "=== docker health check start ==="

  if ! "$DOCKER" info >/dev/null 2>&1; then
    start_container_manager
    if ! wait_for_docker; then
      log "ERROR: docker daemon not ready"
      ntfy_alert "NAS Docker down" "Container Manager failed to start on TabaskaNAS" 5
      exit 1
    fi
  fi

  bring_up_stacks

  local down=()
  local row name host port codes
  for row in "${CHECKS[@]}"; do
    IFS=':' read -r name host port codes <<< "$row"
    check_port "$name" "$host" "$port" "$codes" || down+=("$name")
  done

  if ((${#down[@]})); then
    log "FAIL: ${#down[@]} service(s) still down: ${down[*]}"
    ntfy_alert "NAS services down" "Still down after compose up: ${down[*]}" 5
    exit 1
  fi

  log "PASS: all monitored ports responding"
}

main "$@"
