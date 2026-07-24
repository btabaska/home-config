#!/usr/bin/env bash
# immich-ml-window.sh — glue-14 (2026-07-24)
# Time-gate the Immich remote-ML container on the rig's RTX 3090 Ti to a NIGHT
# window only. Photos are the LOWEST-priority GPU tenant: a 24B chat/coding model
# needs ~22G of the 24G card and Immich ML needs ~13G, so they cannot coexist.
#
#   off (07:00 EDT) — pause the ML-GPU job queues, then STOP the container.
#                     Immich falls back to the NAS iGPU (OpenVINO): interactive
#                     search stays ~225ms warm, batch indexing waits for tonight,
#                     and the rig GPU is 100% free for chat/coding/ComfyUI.
#   on  (01:00 EDT) — START the container, wait for it to answer /ping, then
#                     RESUME the queues so any new-photo backlog crunches fast on
#                     the 3090 Ti while nobody is using it.
#
# EnvironmentFile /etc/immich-ml-window.env supplies IMMICH_URL + IMMICH_API_KEY
# (a least-privilege key: job.create + job.read only — vault
# immich.rig_ml_window_api_key). Idempotent; safe to re-run in either state.
#
# Canonical source: foss-setup/configs/host/rig/immich-ml/immich-ml-window.sh
# Deploy: install -m 755 to /usr/local/bin/immich-ml-window.sh on the rig.
set -euo pipefail

CONTAINER=immich_machine_learning
ML_PING=http://192.168.10.12:3003/ping
# The ML-GPU-bound queues (each POSTs to the ML /predict endpoint). thumbnail /
# metadata / video queues run on the NAS server CPU and are left alone.
QUEUES=(smartSearch faceDetection ocr)

: "${IMMICH_URL:?set IMMICH_URL in /etc/immich-ml-window.env}"
: "${IMMICH_API_KEY:?set IMMICH_API_KEY in /etc/immich-ml-window.env}"

log(){ echo "[immich-ml-window] $*"; }
rc=0

queue_cmd(){  # $1 = pause|resume
  local cmd="$1" q code
  for q in "${QUEUES[@]}"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 -X PUT \
      "$IMMICH_URL/api/jobs/$q" \
      -H "x-api-key: $IMMICH_API_KEY" -H 'Content-Type: application/json' \
      -d "{\"command\":\"$cmd\",\"force\":false}" 2>/dev/null || echo 000)
    if [ "$code" = 200 ] || [ "$code" = 204 ]; then
      log "queue $q $cmd -> $code"
    else
      log "queue $q $cmd -> $code (FAILED)"; rc=1
    fi
  done
}

case "${1:-}" in
  on)
    log "NIGHT: starting $CONTAINER"
    docker start "$CONTAINER" >/dev/null
    for _ in $(seq 1 30); do
      curl -s -m 5 "$ML_PING" 2>/dev/null | grep -q pong && break
      sleep 2
    done
    curl -s -m 5 "$ML_PING" 2>/dev/null | grep -q pong \
      && log "NIGHT: $CONTAINER answering /ping" \
      || { log "NIGHT: WARNING $CONTAINER not answering /ping after 60s"; rc=1; }
    queue_cmd resume
    ;;
  off)
    log "DAY: pausing ML-GPU queues then stopping $CONTAINER"
    queue_cmd pause     # pause first so no job dies mid-encode when the container stops
    docker stop "$CONTAINER" >/dev/null
    log "DAY: $CONTAINER stopped — Immich now uses the NAS iGPU fallback"
    ;;
  *)
    echo "usage: $0 on|off" >&2; exit 2 ;;
esac

exit "$rc"
