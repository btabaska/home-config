#!/usr/bin/env bash
# ==============================================================================
# rclone-seedbox-mount.sh — persistent rclone SFTP mount of the seedbox files
# ==============================================================================
# Phase 2. Runs ON THE NAS (DS920+). Mounts the seedbox's completed-downloads
# folder so the home *arr stack can READ finished downloads for import:
#
#     seedbox:/home/hd34/btabaska/files  ->  /volume1/mounts/seedbox-files
#
# The *arr containers bind this host path to /seedbox:rslave. Their Remote Path
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
# (Install rclone on DSM via the SynoCommunity package or the static binary.)
# On a systemd host instead, wrap this in a simple oneshot service (Type=forking).
#
# Docs: https://rclone.org/commands/rclone_mount/  |  https://rclone.org/sftp/
# ==============================================================================
set -euo pipefail

# --- config (override via environment if needed) ------------------------------
REMOTE="${REMOTE:-seedbox:/home/hd34/btabaska/files}"   # rclone remote:path (see rclone.conf)
MOUNTPOINT="${MOUNTPOINT:-/volume1/mounts/seedbox-files}"
RCLONE="${RCLONE:-/usr/local/bin/rclone}"               # TODO: adjust to your rclone path (`which rclone`)
RCLONE_CONF="${RCLONE_CONF:-/root/.config/rclone/rclone.conf}"
LOG="${LOG:-/var/log/rclone-seedbox.log}"

mkdir -p "$MOUNTPOINT"

# Already mounted? Nothing to do. (mountpoint(1) is the reliable check.)
if mountpoint -q "$MOUNTPOINT"; then
  echo "$(date -Is) already mounted at $MOUNTPOINT" >>"$LOG"
  exit 0
fi

# Clean up a stale/half-dead FUSE handle before remounting (ignore errors).
fusermount -uz "$MOUNTPOINT" 2>/dev/null || umount -l "$MOUNTPOINT" 2>/dev/null || true

echo "$(date -Is) mounting $REMOTE -> $MOUNTPOINT" >>"$LOG"

# --allow-other      : so the *arr containers' PUID/PGID can read the mount
#                      (requires `user_allow_other` in /etc/fuse.conf on the host)
# --vfs-cache-mode writes : safe writes (Unpackerr extraction) + reliable reads
# --dir-cache-time 1m     : pick up newly-completed downloads quickly
# --buffer-size 64M       : per-file read-ahead for smooth import copies
exec "$RCLONE" mount "$REMOTE" "$MOUNTPOINT" \
  --config "$RCLONE_CONF" \
  --allow-other \
  --vfs-cache-mode writes \
  --dir-cache-time 1m \
  --buffer-size 64M \
  --log-file "$LOG" \
  --log-level INFO \
  --daemon
