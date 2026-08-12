#!/bin/bash
# resume-games.sh — sequential resume (2026-08-11 21:45) of the two seedbox->NAS
# game transfers that were SIGTERMed at 13:54:39 (collateral of the seedbox
# rclone-mount remount cycle). Runs them ONE AT A TIME — two concurrent rclone
# transfer jobs on /volume1 is a known deadlock hazard, and running both at
# once is what the killed first attempt did. Both child scripts are idempotent
# (rclone copy/move skip already-transferred files) and own their STATUS files.
# Launched as root via: setsid nohup bash resume-games.sh
set -u
DIR=/volume1/games/.rom-import
LOG=$DIR/resume-games.log
ts(){ printf '%s %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

notify(){ # best-effort ntfy, reusing the docker-health script's config
  local title="$1" msg="$2"
  [ -r /volume1/scripts/nas/health.env ] && . /volume1/scripts/nas/health.env
  [ -n "${NTFY_URL:-}" ] && [ -n "${NTFY_TOPIC:-}" ] || return 0
  local args=(-fsS -m 15 -H "Title: ${title}" -d "$msg")
  [ -n "${NTFY_TOKEN:-}" ] && args+=(-H "Authorization: Bearer ${NTFY_TOKEN}")
  curl "${args[@]}" "${NTFY_URL}/${NTFY_TOPIC}" >/dev/null 2>&1 || ts "WARN: ntfy publish failed"
}

ts "=== resume-games start ==="
echo "QUEUED behind import-v3 (resume $(date '+%F %T'))" > "$DIR/STATUS-move"

bash "$DIR/import-roms-v3.sh"
ts "import-roms-v3 finished: $(cat "$DIR/STATUS-v3" 2>/dev/null)"

bash "$DIR/move-games.sh"
ts "move-games finished: $(cat "$DIR/STATUS-move" 2>/dev/null)"

notify "NAS games transfer finished" "import-v3: $(cat "$DIR/STATUS-v3" 2>/dev/null) | move: $(cat "$DIR/STATUS-move" 2>/dev/null)"
ts "=== resume-games end ==="
