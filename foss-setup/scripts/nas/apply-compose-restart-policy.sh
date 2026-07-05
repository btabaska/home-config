#!/usr/bin/env bash
# Apply updated compose files (restart: always) on the NAS without recreating containers.
# Run on NAS as root: sudo bash /volume1/scripts/nas/apply-compose-restart-policy.sh
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

DOCKER="${DOCKER:-/usr/local/bin/docker}"
COMPOSE="${COMPOSE:-/usr/local/bin/docker compose}"

log() { printf '[%s] %s\n' "$(date -Is)" "$*"; }

compose_up() {
  local dir="$1"
  shift
  [[ -d "$dir" ]] || { log "Skip — missing $dir"; return 0; }

  if [[ -f "$dir/docker-compose.yml" ]]; then
    log "compose up (no-recreate): $dir"
    $COMPOSE -f "$dir/docker-compose.yml" up -d --no-recreate "$@"
    return
  fi

  if [[ -f "$dir/compose.yaml" ]]; then
    log "compose up (no-recreate): $dir"
    local files=(-f "$dir/compose.yaml")
    [[ -f "$dir/compose.nas.yaml" ]] && files+=(-f "$dir/compose.nas.yaml")
    $COMPOSE "${files[@]}" up -d --no-recreate "$@"
  fi
}

main() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Run as root: sudo bash $0" >&2
    exit 1
  fi

  compose_up /volume1/docker/media-automation
  compose_up /volume1/docker/stash
  compose_up /volume1/docker/calibre-web-automated
  compose_up /volume1/docker/dependency-track
  compose_up /volume1/docker/immich

  log "Ensuring restart=always on all running containers..."
  mapfile -t ids < <("$DOCKER" ps -q)
  if ((${#ids[@]})); then
    "$DOCKER" update --restart=always "${ids[@]}"
  fi

  log "Done. Restart policies:"
  "$DOCKER" ps --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}'
}

main "$@"
