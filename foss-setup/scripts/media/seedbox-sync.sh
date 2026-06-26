#!/usr/bin/env bash
#
# seedbox-sync.sh — pull finished, named media from the off-site seedbox to the NAS via rclone+SFTP.
#                   Phase 2. Runs ON THE NAS (the puller). Designed for cron. Idempotent.
#
# Why copy (not sync): the seedbox keeps seeding the original files for ratio. We pull a COPY down
# to the NAS library; we never mirror-delete the seedbox. `rclone copy` skips already-transferred
# files (size + mod-time), so re-running is cheap and safe.
#   rclone copy:  https://rclone.org/commands/rclone_copy/
#   rclone sync:  https://rclone.org/commands/rclone_sync/   (NOT used here — it would delete)
#   SFTP backend: https://rclone.org/sftp/
#
# Transfer rides the Tailscale tailnet (set the SFTP host in rclone.conf to the seedbox's
# Tailscale name/IP) so nothing is exposed to the internet. SFTP is encrypted regardless.
#
# GUI ALTERNATIVE — Syncthing:
#   Prefer a GUI / continuous push instead of cron-pull? Run Syncthing on BOTH the seedbox and the
#   NAS. On the seedbox share the media folder as **Send Only**; on the NAS set the same folder
#   **Receive Only** + file versioning. Syncthing then continuously mirrors finished files down with
#   no scripting. Use one or the other, not both, for a given folder.
#     Getting started: https://docs.syncthing.net/intro/getting-started.html
#     Folder types:    https://docs.syncthing.net/users/foldertypes.html
#
# ---------------------------------------------------------------------------------------------------
# Setup (once, on the NAS):
#   1. Install rclone:        https://rclone.org/install/
#   2. Create the remote:     cp configs/seedbox/rclone.conf.example ~/.config/rclone/rclone.conf
#                             # edit placeholders, then: chmod 600 ~/.config/rclone/rclone.conf
#   3. Test it:               rclone lsd seedbox:
#
# Run (manual dry-run first!):
#   DRY_RUN=1 ./seedbox-sync.sh
#   ./seedbox-sync.sh
#
# Cron (every 15 min, log to file):
#   */15 * * * * RCLONE_REMOTE=seedbox /volume1/scripts/media/seedbox-sync.sh >> /var/log/seedbox-sync.log 2>&1
#
# A lockfile prevents overlapping runs (a slow pull won't stack up under cron).

set -euo pipefail

# --- Configuration via environment (override before calling or in the crontab line) --------------
# Name of the rclone remote defined in rclone.conf (see rclone.conf.example).
RCLONE_REMOTE="${RCLONE_REMOTE:-seedbox}"

# Path on the SEEDBOX (relative to the SFTP user's home unless it starts with '/').
# These are the *named/organized* library folders the *arr apps write to — NOT the torrents dir.
REMOTE_MOVIES="${REMOTE_MOVIES:-data/media/movies}"
REMOTE_TV="${REMOTE_TV:-data/media/tv}"

# Destination paths on the NAS (your Plex library roots).
LOCAL_MOVIES="${LOCAL_MOVIES:-/volume1/media/movies}"
LOCAL_TV="${LOCAL_TV:-/volume1/media/tv}"

# rclone tuning. SFTP needs connections >= transfers+checkers+1 (see rclone SFTP docs).
TRANSFERS="${TRANSFERS:-4}"
CHECKERS="${CHECKERS:-8}"
BWLIMIT="${BWLIMIT:-}"            # e.g. "50M" to cap; empty = no cap (seedbox is the bottleneck, not home)
MIN_AGE="${MIN_AGE:-1m}"          # ignore files still being written/imported on the seedbox
LOCKFILE="${LOCKFILE:-/tmp/seedbox-sync.lock}"
DRY_RUN="${DRY_RUN:-0}"           # set to 1 to preview without transferring

# --- Preconditions --------------------------------------------------------------------------------
command -v rclone >/dev/null 2>&1 || { echo "ERROR: rclone not installed (https://rclone.org/install/)" >&2; exit 1; }
command -v flock  >/dev/null 2>&1 || { echo "ERROR: flock not available" >&2; exit 1; }

log() { printf '%s [seedbox-sync] %s\n' "$(date -Is)" "$*"; }

# Verify the remote exists in rclone's config.
if ! rclone listremotes 2>/dev/null | grep -qx "${RCLONE_REMOTE}:"; then
  echo "ERROR: rclone remote '${RCLONE_REMOTE}:' not found. Create it from rclone.conf.example." >&2
  exit 1
fi

# Build the optional/flag arguments as an array (safe word-splitting).
RCLONE_ARGS=(
  --transfers "${TRANSFERS}"
  --checkers "${CHECKERS}"
  --sftp-connections "$((TRANSFERS + CHECKERS + 1))"
  --min-age "${MIN_AGE}"
  --copy-links            # follow any symlinks the *arr import created
  --create-empty-src-dirs=false
  --stats 30s
  --stats-one-line
  -v
)
[[ -n "${BWLIMIT}" ]] && RCLONE_ARGS+=( --bwlimit "${BWLIMIT}" )
[[ "${DRY_RUN}" == "1" ]] && { RCLONE_ARGS+=( --dry-run ); log "DRY-RUN mode: no files will be transferred."; }

# --- One transfer pair: copy REMOTE -> LOCAL (idempotent; never deletes the seedbox) -------------
pull() {
  local remote_sub="$1" local_dir="$2" label="$3"
  log "Pulling ${label}: ${RCLONE_REMOTE}:${remote_sub} -> ${local_dir}"
  mkdir -p "${local_dir}"
  # `copy` adds/updates only; it will not delete anything on either side.
  rclone copy "${RCLONE_REMOTE}:${remote_sub}" "${local_dir}" "${RCLONE_ARGS[@]}"
  log "Done: ${label}"
}

main() {
  log "Starting (remote=${RCLONE_REMOTE})."
  pull "${REMOTE_MOVIES}" "${LOCAL_MOVIES}" "movies"
  pull "${REMOTE_TV}"     "${LOCAL_TV}"     "tv"
  log "All transfers complete."
  # Plex import: the NAS Plex usually auto-detects new files (inotify). If yours doesn't,
  # trigger a partial scan here, e.g.:
  #   curl -s "http://localhost:32400/library/sections/<ID>/refresh?X-Plex-Token=<TOKEN>" >/dev/null
}

# --- Run under a non-blocking lock so cron runs never overlap ------------------------------------
exec 9>"${LOCKFILE}"
if ! flock -n 9; then
  log "Another run holds the lock (${LOCKFILE}); exiting."
  exit 0
fi

main "$@"
