#!/usr/bin/env bash
# ==============================================================================
# rclone-seedbox-mount.sh — persistent rclone SFTP mount of the seedbox files
# ==============================================================================
# Phase 2. Runs ON THE NAS (DS920+). Mounts the seedbox's completed-downloads
# folder so the home *arr stack can READ finished downloads for import:
#
#     seedbox:/home/hd34/btabaska/files  ->  /volume1/mounts/seedbox-files
#
# The *arr containers bind this host path to /seedbox. Their Remote Path
# Mapping (/home/hd34/btabaska/files/ -> /seedbox/) makes the path Deluge
# reports resolve here.
#
# !!! A DROPPED OR STALE MOUNT SILENTLY STALLS ALL IMPORTS !!!
# If this FUSE mount goes away, the bind target becomes an empty dir and every
# *arr import quietly does nothing (no error). That is why:
#   - this unit/task starts at boot, and
#   - rclone-seedbox-watchdog.sh re-runs it if the mountpoint is empty/stale.
#
# DSM SETUP (Synology has no systemd): Control Panel -> Task Scheduler ->
#   Create -> Triggered Task -> User-defined script, Event = Boot-up, User = root,
#   Command = /volume1/scripts/media/rclone-seedbox-mount.sh
#
# SAFETY CONTRACT:
#   - This script ONLY mounts. It NEVER tears down a live mount.
#   - Stale-mount detection is the watchdog's job.
#   - Running this script when already mounted is a safe no-op (exit 0).
#
# Docs: https://rclone.org/commands/rclone_mount/  |  https://rclone.org/sftp/
# ==============================================================================
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

# --- config (override via environment if needed) ------------------------------
REMOTE="${REMOTE:-seedbox:/home/hd34/btabaska/files}"
MOUNTPOINT="${MOUNTPOINT:-/volume1/mounts/seedbox-files}"
RCLONE="${RCLONE:-/usr/local/bin/rclone}"
RCLONE_CONF="${RCLONE_CONF:-/root/.config/rclone/rclone.conf}"
LOG="${LOG:-/var/log/rclone-seedbox.log}"
HEALTH_FILE="${HEALTH_FILE:-/var/run/seedbox-mount.ok}"
COMPOSE_FILE="${COMPOSE_FILE:-/volume1/docker/media-automation/docker-compose.yml}"
DOCKER="${DOCKER:-/usr/local/bin/docker}"

# Rotate log if it exceeds 10 MB to prevent unbounded growth on DSM.
if [[ -f "$LOG" ]] && (( $(stat -c%s "$LOG" 2>/dev/null || echo 0) > 10485760 )); then
  mv "$LOG" "${LOG}.1"
fi

mkdir -p "$MOUNTPOINT"

# is_mountpoint: check kernel mountinfo and /proc/mounts — no SFTP I/O.
# Never uses `ls` so it cannot be fooled by a slow SFTP session.
is_mountpoint() {
  local mp="${1%/}"
  # /proc/self/mountinfo field 5 = mount point
  if awk -v mp="$mp" '$5 == mp { found=1 } END { exit !found }' /proc/self/mountinfo 2>/dev/null; then
    return 0
  fi
  # /proc/mounts field 2 = mount point
  if awk -v mp="$mp" '$2 == mp { found=1 } END { exit !found }' /proc/mounts 2>/dev/null; then
    return 0
  fi
  if command -v mountpoint >/dev/null 2>&1 && mountpoint -q "$mp" 2>/dev/null; then
    return 0
  fi
  return 1
}

restart_download_containers() {
  [[ -f "$COMPOSE_FILE" ]] || return 0
  echo "$(date -Is) INFO: restarting download-touching containers (post-remount)" >>"$LOG"
  "$DOCKER" compose -f "$COMPOSE_FILE" restart sonarr radarr lidarr readarr unpackerr >>"$LOG" 2>&1 \
    || echo "$(date -Is) WARN: container restart failed — run manually: docker compose restart sonarr radarr lidarr readarr unpackerr" >>"$LOG"
}

# ---- SAFETY GUARD: never remount if kernel already shows the FUSE mount -----
# We check mountinfo only (no SFTP ls). The watchdog handles stale-handle
# detection and calls this script only after it has already torn down a dead
# FUSE handle. So if we see a mountpoint here, it is either healthy or the
# watchdog is about to handle it — either way, do not touch it.
if is_mountpoint "$MOUNTPOINT"; then
  echo "$(date -Is) INFO: already mounted at $MOUNTPOINT — no-op" >>"$LOG"
  exit 0
fi

# ---- Ensure fusermount3 exists (DSM ships fusermount only) ------------------
if ! command -v fusermount3 >/dev/null 2>&1; then
  local_fusermount="$(command -v fusermount || true)"
  if [[ -n "$local_fusermount" ]]; then
    ln -sf "$local_fusermount" /usr/local/bin/fusermount3
    echo "$(date -Is) INFO: created fusermount3 symlink -> $local_fusermount" >>"$LOG"
  else
    echo "$(date -Is) ERROR: no fusermount binary found; cannot mount FUSE" >>"$LOG"
    exit 1
  fi
fi

# ---- Ensure user_allow_other in /etc/fuse.conf (for PUID containers) --------
# Append ONLY if not already present (idempotent — allow leading whitespace).
if [[ -f /etc/fuse.conf ]] && ! grep -qE '^[[:space:]]*user_allow_other' /etc/fuse.conf 2>/dev/null; then
  echo 'user_allow_other' >> /etc/fuse.conf
  echo "$(date -Is) INFO: added user_allow_other to /etc/fuse.conf" >>"$LOG"
fi

# ---- Verify rclone binary ---------------------------------------------------
if [[ ! -x "$RCLONE" ]]; then
  echo "$(date -Is) ERROR: rclone not found at $RCLONE" >>"$LOG"
  exit 1
fi

# ---- Clean up any ghost FUSE handle (ignore errors) -------------------------
fusermount -uz "$MOUNTPOINT" 2>/dev/null || umount -l "$MOUNTPOINT" 2>/dev/null || true

echo "$(date -Is) INFO: mounting $REMOTE -> $MOUNTPOINT" >>"$LOG"

# rclone mount flags:
#   --allow-other          : *arr containers (PUID != root) can read the mount
#   --vfs-cache-mode full  : cache file DATA on disk, not just metadata. RETUNED
#                            2026-07-10 (was `minimal`, chosen when the DS920+
#                            had 4 GB — it now has ~20 GB). `minimal` re-read
#                            every byte over SFTP on each scan/analyze/import-
#                            copy; with SQLite locks held during those reads it
#                            was a prime driver of the import-queue freezes.
#                            `full` serves repeat reads (media-info parse, then
#                            the import copy) from the local cache → far less
#                            network I/O and lock-hold time. Read-only workload,
#                            so this only ever caches downloads being imported.
#   --vfs-cache-max-size 50G : hard cap the cache on /volume1 (won't fill the
#                            volume; the 2026-07-07 fill was the cache-dir being
#                            on the tiny system partition — fixed separately).
#   --vfs-cache-max-age 24h : evict cached files a day after last use.
#   --dir-cache-time 3m    : SFTP has no change-notify, so this is the max time
#                            to SEE a newly-completed download. 3m (was 1m)
#                            cuts constant re-listing; import latency is bounded
#                            by it, fine for TV/movies.
#   --buffer-size 64M      : per-open-file read-ahead (was 32M; more RAM now).
#   --timeout 60s          : global I/O timeout per operation
#   --contimeout 15s       : SFTP connection timeout (fail fast on network loss)
#   --low-level-retries 3  : retry transient SFTP errors at the transport layer
#   --retries 2            : retry at the rclone operation layer
#   --sftp-idle-timeout 60s: kill idle SFTP connections so they don't go stale
#   --log-level INFO       : mount events + errors go to LOG
#   --daemon               : backgrounds immediately; kernel signals readiness
# --cache-dir on the data volume: rclone defaults to /root/.cache on the tiny
# DSM system partition — it filled it to 100% on 2026-07-07 and broke DSM apps.
CACHE_DIR="${CACHE_DIR:-/volume1/cache/rclone}"
mkdir -p "$CACHE_DIR"
"$RCLONE" mount "$REMOTE" "$MOUNTPOINT" \
  --config "$RCLONE_CONF" \
  --allow-other \
  --cache-dir "$CACHE_DIR" \
  --vfs-cache-mode full \
  --vfs-cache-max-size 50G \
  --vfs-cache-max-age 24h \
  --dir-cache-time 3m \
  --buffer-size 64M \
  --timeout 60s \
  --contimeout 15s \
  --low-level-retries 3 \
  --retries 2 \
  --sftp-idle-timeout 60s \
  --log-file "$LOG" \
  --log-level INFO \
  --daemon

# --daemon returns as soon as the FUSE device is registered with the kernel.
# Wait for /proc/self/mountinfo to confirm — this is fast (no SFTP I/O) and
# reliable. We do NOT do an `ls` here; `ls` can be slow if SFTP negotiation is
# still in progress, and a timeout here would exit 1 while rclone is still
# starting up (leaving an orphaned daemon). The watchdog will verify readiness
# with `ls` on the next cycle (within 5 min).
WAIT_SECS=30
for i in $(seq 1 "$WAIT_SECS"); do
  if is_mountpoint "$MOUNTPOINT"; then
    echo "$(date -Is) INFO: FUSE handle registered after ${i}s — mount started" >>"$LOG"
    break
  fi
  sleep 1
done

if ! is_mountpoint "$MOUNTPOINT"; then
  echo "$(date -Is) ERROR: rclone daemon started but FUSE mount not in mountinfo after ${WAIT_SECS}s" >>"$LOG"
  grep -F "$MOUNTPOINT" /proc/self/mountinfo >>"$LOG" 2>&1 || true
  exit 1
fi

echo "$(date -Is) INFO: mount registered — SFTP handshake may still be in progress; watchdog will verify" >>"$LOG"

# Update health marker so the watchdog and external monitors have a reference.
date -Is > "$HEALTH_FILE"

restart_download_containers
