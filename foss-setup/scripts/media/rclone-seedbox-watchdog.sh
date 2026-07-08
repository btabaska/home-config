#!/usr/bin/env bash
# ==============================================================================
# rclone-seedbox-watchdog.sh — self-heal the seedbox rclone mount
# ==============================================================================
# Phase 2. Runs ON THE NAS (DS920+), every 5 min via DSM Task Scheduler.
#
# A dropped/stale rclone FUSE mount does NOT raise an error in the *arrs — it
# just makes /seedbox look empty, so imports silently stall forever. This
# watchdog detects that state and remounts.
#
# HEALTH LOGIC (two-strike before remount):
#   Healthy  : mountinfo shows FUSE mount AND `ls` succeeds within 20 s
#   Suspect  : mountinfo shows mount BUT `ls` times out/fails (SFTP may be
#              slow — SFTP lag of up to 20 s happens on cold sessions over WAN)
#   Unhealthy: not in mountinfo at all, OR suspect for 2+ consecutive cycles
#
# Two-strike rule prevents tearing down a live mount just because the SFTP
# session was slow. The state file /var/run/seedbox-watchdog.fail_count persists
# between invocations (cleared on success, incremented on Suspect).
#
# DSM SETUP: Control Panel -> Task Scheduler -> Create -> Scheduled Task ->
#   User-defined script, User = root, repeat every 5 minutes,
#   Command = /volume1/scripts/media/rclone-seedbox-watchdog.sh
# ==============================================================================
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

MOUNTPOINT="${MOUNTPOINT:-/volume1/mounts/seedbox-files}"
MOUNT_SCRIPT="${MOUNT_SCRIPT:-/volume1/scripts/media/rclone-seedbox-mount.sh}"
LOG="${LOG:-/var/log/rclone-seedbox.log}"
HEALTH_FILE="${HEALTH_FILE:-/var/run/seedbox-mount.ok}"
FAIL_COUNT_FILE="${FAIL_COUNT_FILE:-/var/run/seedbox-watchdog.fail_count}"
COMPOSE_FILE="${COMPOSE_FILE:-/volume1/docker/media-automation/docker-compose.yml}"
DOCKER="${DOCKER:-/usr/local/bin/docker}"

# LS_TIMEOUT: how long to wait for the seedbox SFTP dir listing before
# declaring the mount suspect. 20 s is generous for WAN SFTP; keep it below
# the 5-min scheduler interval.
LS_TIMEOUT=20

ts() { date -Is; }

# Single-instance guard: a hung SFTP probe can outlive the 5-min scheduler
# interval and stack watchdogs (each then tearing down the other's remount).
LOCK_FILE="${LOCK_FILE:-/var/run/seedbox-watchdog.lock}"
exec 9>"$LOCK_FILE"
if command -v flock >/dev/null 2>&1 && ! flock -n 9; then
  echo "$(ts) INFO: watchdog already running — skipping this cycle" >>"$LOG"
  exit 0
fi

is_mountpoint() {
  local mp="${1%/}"
  if awk -v mp="$mp" '$5 == mp { found=1 } END { exit !found }' /proc/self/mountinfo 2>/dev/null; then
    return 0
  fi
  if awk -v mp="$mp" '$2 == mp { found=1 } END { exit !found }' /proc/mounts 2>/dev/null; then
    return 0
  fi
  if command -v mountpoint >/dev/null 2>&1 && mountpoint -q "$mp" 2>/dev/null; then
    return 0
  fi
  return 1
}

# ls_ok: returns 0 if the dir listing succeeds within LS_TIMEOUT seconds.
# A non-empty result is logged so we can see file count trends.
ls_ok() {
  local out
  if command -v timeout >/dev/null 2>&1; then
    out=$(timeout "$LS_TIMEOUT" ls -1 "$MOUNTPOINT" 2>/dev/null) || return 1
  else
    out=$(ls -1 "$MOUNTPOINT" 2>/dev/null) || return 1
  fi
  local count
  count=$(echo "$out" | grep -c .) || count=0
  # The remote is never legitimately empty — an empty listing IS the silent
  # stall this watchdog exists to catch (a dead VFS returns 0 entries + rc 0).
  (( count > 0 )) || { echo "$(ts) WARN: watchdog listing EMPTY — treating as stall" >>"$LOG"; return 1; }

  # READ probe, not just a listing: on 2026-07-05..07 the SFTP session served
  # corrupted reads (rardecode checksum failures broke unpackerr for 2 days)
  # while `ls` kept succeeding — a listing-only check can't see a bad session.
  # Reading real bytes through the VFS exercises the data path.
  local probe
  probe=$(timeout "${FIND_TIMEOUT:-60}" find "$MOUNTPOINT" -type f -size +1M 2>/dev/null | head -1) || true
  if [[ -n "$probe" ]]; then
    if ! timeout "${READ_TIMEOUT:-30}" head -c 262144 "$probe" >/dev/null 2>&1; then
      echo "$(ts) WARN: watchdog read-probe FAILED on $probe — listing ok but data path is bad" >>"$LOG"
      return 1
    fi
  fi

  echo "$(ts) INFO: watchdog ls+read ok — $count top-level entries in $MOUNTPOINT" >>"$LOG"
  # Write health marker with timestamp and entry count.
  printf '%s entries=%d\n' "$(ts)" "$count" > "$HEALTH_FILE"
  return 0
}

get_fail_count() {
  if [[ -f "$FAIL_COUNT_FILE" ]]; then
    local n
    # cat may race with clear_fail_count; a read failure just means "no count".
    n=$(cat "$FAIL_COUNT_FILE" 2>/dev/null || true)
    if [[ "$n" =~ ^[0-9]+$ ]]; then
      echo "$n"
      return
    fi
  fi
  echo 0
}

set_fail_count() { echo "$1" > "$FAIL_COUNT_FILE"; }
clear_fail_count() { rm -f "$FAIL_COUNT_FILE"; }

restart_download_containers() {
  [[ -f "$COMPOSE_FILE" ]] || return 0
  echo "$(ts) INFO: restarting download-touching containers (post-remount)" >>"$LOG"
  "$DOCKER" compose -f "$COMPOSE_FILE" restart sonarr radarr lidarr readarr unpackerr >>"$LOG" 2>&1 \
    || echo "$(ts) WARN: container restart failed — run manually: docker compose restart sonarr radarr lidarr readarr unpackerr" >>"$LOG"
}

# ---- Case 1: not in mountinfo at all — remount immediately ------------------
if ! is_mountpoint "$MOUNTPOINT"; then
  fail_count=$(get_fail_count)
  echo "$(ts) WATCHDOG: $MOUNTPOINT not mounted (fail_count=$fail_count) — remounting" >>"$LOG"
  rm -f "$HEALTH_FILE"
  clear_fail_count
  # No FUSE handle to tear down; mount script will handle ghost cleanup.
  # mount script restarts the download containers itself; calling it again
  # here doubled arr downtime after every remount (observed 2026-07-05).
  "$MOUNT_SCRIPT" || true
  exit 0
fi

# ---- Case 2: in mountinfo — test SFTP reachability via ls -------------------
if ls_ok; then
  # Healthy: reset failure counter.
  if [[ "$(get_fail_count)" -gt 0 ]]; then
    echo "$(ts) INFO: watchdog: mount healthy again (was suspect) — resetting fail counter" >>"$LOG"
  fi
  clear_fail_count
  exit 0
fi

# ---- Case 3: in mountinfo but ls failed/timed out ---------------------------
fail_count=$(get_fail_count)
fail_count=$(( fail_count + 1 ))
set_fail_count "$fail_count"

if (( fail_count < 2 )); then
  echo "$(ts) WATCHDOG: $MOUNTPOINT suspect — ls timed out or empty (strike $fail_count/2); holding off remount" >>"$LOG"
  # Remove health marker so external monitors see it as stale but don't alert
  # until confirmed unhealthy on next cycle.
  rm -f "$HEALTH_FILE"
  exit 0
fi

# Two consecutive failures — treat as stale/dead handle.
echo "$(ts) WATCHDOG: $MOUNTPOINT confirmed unhealthy (strike $fail_count/2) — tearing down and remounting" >>"$LOG"
clear_fail_count
rm -f "$HEALTH_FILE"

# Tear down the stale FUSE handle. -uz = unmount even if busy, lazy.
fusermount -uz "$MOUNTPOINT" 2>/dev/null \
  || umount -l "$MOUNTPOINT" 2>/dev/null \
  || true

# Give kernel a moment to release the device node before remounting.
sleep 2

"$MOUNT_SCRIPT" && restart_download_containers || true
