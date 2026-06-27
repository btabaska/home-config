#!/usr/bin/env bash
# ==============================================================================
# rclone-seedbox-watchdog.sh — self-heal the seedbox rclone mount
# ==============================================================================
# Phase 2. Runs ON THE NAS (DS920+), on a short schedule (every 5 min).
#
# A dropped/stale rclone FUSE mount does NOT raise an error in the *arrs — it
# just makes /seedbox look empty, so imports silently stall forever. This
# watchdog detects that state and remounts.
#
# It treats the mount as UNHEALTHY when EITHER:
#   (a) the path is not a mountpoint at all, OR
#   (b) it is a mountpoint but `ls` fails / returns nothing (stale handle:
#       the SFTP session died but the kernel still thinks it's mounted).
# In both cases it calls rclone-seedbox-mount.sh (which cleans up + remounts).
#
# DSM SETUP: Control Panel -> Task Scheduler -> Create -> Scheduled Task ->
#   User-defined script, User = root, repeat every 5 minutes,
#   Command = /volume1/scripts/media/rclone-seedbox-watchdog.sh
# On a systemd host instead, use a .timer firing OnUnitActiveSec=5min.
# ==============================================================================
set -uo pipefail

MOUNTPOINT="${MOUNTPOINT:-/volume1/mounts/seedbox-files}"
MOUNT_SCRIPT="${MOUNT_SCRIPT:-/volume1/scripts/media/rclone-seedbox-mount.sh}"
LOG="${LOG:-/var/log/rclone-seedbox.log}"

healthy() {
  mountpoint -q "$MOUNTPOINT" || return 1
  # Stale-handle probe: a live mount lists its root quickly. `timeout` guards
  # against a hung SFTP session blocking the watchdog itself.
  timeout 20 ls -1 "$MOUNTPOINT" >/dev/null 2>&1 || return 1
  return 0
}

if healthy; then
  exit 0
fi

echo "$(date -Is) WATCHDOG: $MOUNTPOINT unhealthy (empty/stale) — remounting" >>"$LOG"
# Tear down any half-dead handle, then remount via the canonical mount script.
fusermount -uz "$MOUNTPOINT" 2>/dev/null || umount -l "$MOUNTPOINT" 2>/dev/null || true
"$MOUNT_SCRIPT"
