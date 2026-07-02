#!/usr/bin/env bash
# Recover Synology Container Manager + NAS compose stacks after dockerd crash.
# Run on the NAS as root (or via: ssh -t nas 'sudo bash -s' < recover-docker-stacks.sh)
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

DOCKER="${DOCKER:-/usr/local/bin/docker}"
COMPOSE="${COMPOSE:-/usr/local/bin/docker compose}"
MEDIA_DIR="${MEDIA_DIR:-/volume1/docker/media-automation}"
CWA_DIR="${CWA_DIR:-/volume1/docker/calibre-web-automated}"
START_SCRIPT="/var/packages/ContainerManager/scripts/start-stop-status"

log() { printf '[%s] %s\n' "$(date -Is)" "$*"; }

start_container_manager() {
  if [[ -x "$START_SCRIPT" ]]; then
    log "Starting Container Manager via start-stop-status..."
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
      log "Docker daemon is ready."
      return 0
    fi
    sleep 2
  done
  log "ERROR: Docker daemon did not become ready within 60s."
  return 1
}

compose_up_media() {
  [[ -f "$MEDIA_DIR/docker-compose.yml" ]] || { log "Skip media-automation — no compose file"; return 0; }
  [[ -f "$MEDIA_DIR/.env" ]] || { log "WARN: $MEDIA_DIR/.env missing"; }

  log "Bringing up media-automation Phase A..."
  $COMPOSE -f "$MEDIA_DIR/docker-compose.yml" up -d prowlarr flaresolverr sonarr radarr

  log "Bringing up media-automation Phase B..."
  $COMPOSE -f "$MEDIA_DIR/docker-compose.yml" up -d lidarr readarr rreading-glasses rreading-glasses-db

  log "Bringing up media-automation Phase C..."
  $COMPOSE -f "$MEDIA_DIR/docker-compose.yml" up -d unpackerr
}

compose_up_cwa() {
  [[ -f "$CWA_DIR/docker-compose.yml" ]] || { log "Skip CWA — no compose file"; return 0; }
  log "Bringing up calibre-web-automated..."
  $COMPOSE -f "$CWA_DIR/docker-compose.yml" up -d
}

verify_ports() {
  log "Running containers:"
  "$DOCKER" ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

  log "Listening app ports:"
  netstat -tln 2>/dev/null | grep -E '7878|8989|9696|8787|8686|8083|8191|8788' || true

  log "Memory:"
  free -m 2>/dev/null || true
}

main() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Run as root: ssh -t nas 'sudo bash -s' < recover-docker-stacks.sh" >&2
    exit 1
  fi

  if ! "$DOCKER" info >/dev/null 2>&1; then
    start_container_manager
    wait_for_docker
  else
    log "Docker daemon already running."
  fi

  compose_up_media
  compose_up_cwa
  verify_ports
  log "Recovery complete."
}

main "$@"
