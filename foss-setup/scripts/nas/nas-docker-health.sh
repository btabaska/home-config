#!/usr/bin/env bash
# NAS Docker stack health check + auto-recovery.
# Idempotent: safe to run every 15 min from DSM Task Scheduler (root).
#
# Brings up all compose stacks, verifies critical LAN ports, and — for a service
# that is down AT THE PORT but whose container is running (an "Up but dead" wedge
# that `compose up --no-recreate` can never fix) — restarts that one container.
# Alerts (ntfy) are BACKED OFF and DEDUPED: a no-op run never pages, a genuine
# down state pages once per incident and then at most every PAGE_BACKOFF, and a
# recovery pages exactly once. See health.env for the ntfy config.
#
# History: before fix-62/SM55 this script checked stash for HTTP 200, but stash
# added auth ~2026-07-22 and now serves a 302 login redirect — a HEALTHY state
# that the old check read as DOWN, so it paged homelab-alerts priority-5 every
# 15 min for hours (a no-op storm: `compose up` cannot "fix" a healthy service,
# and there was no backoff). Fixed here: stash accepts 200,302; restart-not-up
# semantics; per-service backoff state in STATE_DIR.
#
# Install: sudo bash /volume1/scripts/nas/install-nas-docker-health-task.sh
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

DOCKER="${DOCKER:-/usr/local/bin/docker}"
# COMPOSE may be overridden via env as a space-separated command; split into an
# array so the command word and subcommand are passed as separate argv entries.
read -r -a COMPOSE <<< "${COMPOSE:-/usr/local/bin/docker compose}"
LOG="${LOG:-/var/log/nas-docker-health.log}"
ENV_FILE="${ENV_FILE:-/volume1/scripts/nas/health.env}"
START_SCRIPT="/var/packages/ContainerManager/scripts/start-stop-status"

# fix-62/SM55 backoff + restart tuning (override via health.env if ever needed):
STATE_DIR="${STATE_DIR:-/var/lib/nas-docker-health}"
STATE_FILE="${STATE_FILE:-$STATE_DIR/state}"
PAGE_BACKOFF="${PAGE_BACKOFF:-14400}"       # re-page a still-down service at most every 4h
RESTART_BACKOFF="${RESTART_BACKOFF:-1800}"  # restart the same wedged container at most every 30m
RESTART_MIN_DOWN="${RESTART_MIN_DOWN:-900}" # only restart after it has been down >=1 prior run (15m)

# name:host:port:acceptable_http_codes (comma-separated, e.g. 200,302,401)
# stash: 302 = healthy login redirect since auth was enabled (fix-62/SM55).
CHECKS=(
  "sonarr:127.0.0.1:8989:200,302"
  "radarr:127.0.0.1:7878:200,302"
  "lidarr:127.0.0.1:8686:200,302"
  "bookshelf:127.0.0.1:8790:200,302"
  "prowlarr:127.0.0.1:9696:200,302"
  "flaresolverr:127.0.0.1:8191:200"
  "immich:127.0.0.1:2283:200"
  "stash:127.0.0.1:9999:200,302"
  "cwa:127.0.0.1:8083:200,302"
  "plex:127.0.0.1:32400:200,401"
)

# service-name -> docker container name, for restart-not-up. plex is a Synology
# package (no container) and is intentionally absent — it is reported but never
# auto-restarted here.
declare -A CONTAINER_OF=(
  [sonarr]=sonarr [radarr]=radarr [lidarr]=lidarr [bookshelf]=bookshelf
  [prowlarr]=prowlarr [flaresolverr]=flaresolverr [immich]=immich_server
  [stash]=stash [cwa]=calibre-web-automated
)

ts() { date -Is; }
log() { printf '[%s] %s\n' "$(ts)" "$*" | tee -a "$LOG"; }

load_env() {
  # Missing env file is fine (alerts just stay disabled) — must not trip set -e.
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
}

start_container_manager() {
  if [[ -x "$START_SCRIPT" ]]; then
    log "Starting Container Manager..."
    # A failed start is handled by wait_for_docker below — don't trip set -e here.
    "$START_SCRIPT" start || log "WARN: start-stop-status start returned non-zero"
    return
  fi
  log "Starting Container Manager via synopkg..."
  /usr/syno/bin/synopkg start ContainerManager || log "WARN: synopkg start returned non-zero"
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
    "${COMPOSE[@]}" -f "$dir/docker-compose.yml" up -d --no-recreate >>"$LOG" 2>&1 \
      || log "WARN: compose up failed for $dir"
    return
  fi

  if [[ -f "$dir/compose.yaml" ]]; then
    local files=(-f "$dir/compose.yaml")
    [[ -f "$dir/compose.nas.yaml" ]] && files+=(-f "$dir/compose.nas.yaml")
    log "compose up -d: $dir"
    "${COMPOSE[@]}" "${files[@]}" up -d --no-recreate >>"$LOG" 2>&1 \
      || log "WARN: compose up failed for $dir"
  fi
}

bring_up_stacks() {
  compose_up_dir /volume1/docker/media-automation
  compose_up_dir /volume1/docker/immich
  compose_up_dir /volume1/docker/stash
  compose_up_dir /volume1/docker/calibre-web-automated
  # dependency-track RETIRED 2026-07-11 — do not auto-recover it
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

# probe one port; echoes nothing, returns 0 if the HTTP code is acceptable.
probe_port() {
  local host="$1" port="$2" allowed="$3" code
  code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 \
    "http://${host}:${port}/" 2>/dev/null) || code="000"
  code_ok "$code" "$allowed" && { echo "$code"; return 0; }
  echo "$code"; return 1
}

container_running() {
  local name="$1"
  [[ "$("$DOCKER" inspect -f '{{.State.Running}}' "$name" 2>/dev/null)" == "true" ]]
}

ntfy_alert() {
  local title="$1" message="$2" priority="${3:-4}"
  [[ -n "${NTFY_URL:-}" && -n "${NTFY_TOPIC:-}" ]] || return 0

  local args=(-sS -X POST "${NTFY_URL%/}/${NTFY_TOPIC}")
  [[ -n "${NTFY_TOKEN:-}" ]] && args+=(-H "Authorization: Bearer ${NTFY_TOKEN}")
  args+=(-H "Title: ${title}" -H "Priority: ${priority}" -d "$message")
  curl "${args[@]}" >/dev/null 2>&1 || log "WARN: ntfy publish failed"
}

# ── backoff state ───────────────────────────────────────────────────────────
# STATE_FILE holds one line per currently-down service:
#   <name> <down_since_epoch> <last_paged_epoch> <last_restart_epoch>
# Absent from the file == currently healthy. This is what makes the alerts
# deduped/backed-off and lets a no-op run stay silent.
declare -A PD_SINCE PD_PAGED PD_RESTART   # prior-run state, loaded below

load_state() {
  [[ -f "$STATE_FILE" ]] || return 0
  local n s p r
  while read -r n s p r; do
    [[ -n "${n:-}" ]] || continue
    PD_SINCE[$n]="${s:-0}"; PD_PAGED[$n]="${p:-0}"; PD_RESTART[$n]="${r:-0}"
  done < "$STATE_FILE"
}

main() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Run as root: sudo bash $0" >&2
    exit 1
  fi

  load_env
  mkdir -p "$STATE_DIR"
  load_state
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

  local now; now=$(date +%s)
  local row name host port codes code
  declare -A IS_DOWN NEW_RESTART HOSTOF PORTOF CODESOF

  # ── phase 1: initial health probe ──────────────────────────────────────────
  for row in "${CHECKS[@]}"; do
    IFS=':' read -r name host port codes <<< "$row"
    HOSTOF[$name]="$host"; PORTOF[$name]="$port"; CODESOF[$name]="$codes"
    if code=$(probe_port "$host" "$port" "$codes"); then
      log "OK   $name ($host:$port) HTTP $code"
    else
      log "DOWN $name ($host:$port) HTTP $code (want $codes)"
      IS_DOWN[$name]=1
    fi
  done

  # ── phase 2: restart-not-up ────────────────────────────────────────────────
  # For a service down NOW that was ALSO down long enough on a prior run, restart
  # its container (compose up --no-recreate can't touch an already-Up container),
  # rate-limited by RESTART_BACKOFF. Re-probe; a recovery clears the down flag.
  for name in "${!IS_DOWN[@]}"; do
    local cname prev_since last_restart
    cname="${CONTAINER_OF[$name]:-}"
    prev_since="${PD_SINCE[$name]:-0}"
    last_restart="${PD_RESTART[$name]:-0}"
    [[ -n "$cname" ]] || continue
    [[ "$prev_since" -gt 0 && $((now - prev_since)) -ge $RESTART_MIN_DOWN ]] || continue
    [[ $((now - last_restart)) -ge $RESTART_BACKOFF ]] || continue
    container_running "$cname" || continue
    log "RESTART $name: down at port but container $cname running — restarting (restart-not-up)"
    "$DOCKER" restart "$cname" >>"$LOG" 2>&1 || log "WARN: restart $cname failed"
    NEW_RESTART[$name]="$now"
    sleep 5
    if code=$(probe_port "${HOSTOF[$name]}" "${PORTOF[$name]}" "${CODESOF[$name]}"); then
      log "OK   $name recovered after restart (HTTP $code)"
      unset "IS_DOWN[$name]"
    else
      log "DOWN $name still down after restart (HTTP $code)"
    fi
  done

  # ── phase 3: paging (backoff + dedup) + state write ────────────────────────
  # Plain strings (not ${#assoc[@]}) so an all-healthy run — where IS_DOWN is a
  # declared-but-unassigned associative array — never trips `set -u` (bash 4.4).
  local page_list="" recovered="" still_down=""
  : > "$STATE_FILE.tmp"
  for row in "${CHECKS[@]}"; do
    IFS=':' read -r name host port codes <<< "$row"
    local prev_since prev_paged last_restart
    prev_since="${PD_SINCE[$name]:-0}"
    prev_paged="${PD_PAGED[$name]:-0}"
    last_restart="${NEW_RESTART[$name]:-${PD_RESTART[$name]:-0}}"
    if [[ -n "${IS_DOWN[$name]:-}" ]]; then
      still_down="$still_down $name"
      local since="$prev_since"
      [[ "$since" -gt 0 ]] || since="$now"          # first time down: stamp now
      local paged="$prev_paged"
      # Page on a NEW incident (was healthy last run) or after the backoff window.
      if [[ "$prev_since" -eq 0 || $((now - prev_paged)) -ge $PAGE_BACKOFF ]]; then
        page_list="$page_list $name"; paged="$now"
      fi
      printf '%s %s %s %s\n' "$name" "$since" "$paged" "$last_restart" >> "$STATE_FILE.tmp"
    else
      # healthy now: if it had been down AND paged, emit exactly one recovery.
      [[ "$prev_since" -gt 0 && "$prev_paged" -gt 0 ]] && recovered="$recovered $name"
    fi
  done
  mv "$STATE_FILE.tmp" "$STATE_FILE"

  # A no-op run (nothing down, nothing recovered) pages NOTHING — the SM55 fix.
  if [[ -n "${recovered# }" ]]; then
    log "RECOVERED:${recovered}"
    ntfy_alert "NAS services recovered" "Back up:${recovered}" 3
  fi
  if [[ -n "${page_list# }" ]]; then
    log "FAIL: paging for still-down service(s):${page_list}"
    ntfy_alert "NAS services down" "Down after self-heal (restart+compose):${page_list}" 5
  fi

  if [[ -n "${still_down# }" ]]; then
    log "STILL-DOWN (tracked, backoff-gated):${still_down}"
    exit 1
  fi
  log "PASS: all monitored ports responding"
}

main "$@"
