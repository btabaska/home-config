#!/usr/bin/env bash
# =============================================================================
# window-maint-unpackerr-rclone.sh — ONE-SHOT windowed maintenance
# =============================================================================
# Runs ON MINI (as btabaska — needs the `nas` ssh alias + known_hosts), drives
# the NAS over ssh. Scheduled for the 4-7AM ET window (08:00-11:00 UTC) via a
# systemd one-shot timer. Two gated phases, each verified, ntfy at every step —
# a silent failure at 4AM is the whole thing we're avoiding.
#
#   PHASE A  clear the unpackerr wedge + apply its new healthcheck
#            (docker rm -f unpackerr times out -> only a dockerd restart frees
#            it; that bounces all NAS containers, hence the window).
#   PHASE B  remount the rclone SFTP mount with the RAM-retuned flags
#            (vfs-cache-mode full etc.) + restart the download-touching
#            containers so they bind the fresh mount (the watchdog's pattern).
#
# Phase B only runs if Phase A fully verifies. Any failure -> high-priority
# ntfy naming the step, and the script stops (leaves the fleet in the last-good
# state for a human/next-session to inspect). DRY_RUN=1 does every read-only
# check + a labeled ntfy test but performs NO restart/remount.
#
# Self-cleaning: on success it disables its own timer so it can't re-fire.
# =============================================================================
set -uo pipefail

DRY_RUN="${DRY_RUN:-0}"
LOG="/var/log/media-window-maint.log"
NAS_SSH=(ssh -o BatchMode=yes -o ConnectTimeout=15 nas)
MOUNTPOINT="/volume1/mounts/seedbox-files"
COMPOSE_DIR="/volume1/docker/media-automation"
DOCKER="/usr/local/bin/docker"
EXPECT_CONTAINERS=23

# --- secrets/env (NAS_SUDO_PASSWORD, NTFY_URL, NTFY_TOKEN) --------------------
# shellcheck disable=SC1091
[ -r /etc/verification/env ] && . /etc/verification/env
: "${NAS_SUDO_PASSWORD:?not set (need /etc/verification/env)}"
NTFY_URL="${NTFY_URL:-http://127.0.0.1:8080/verification}"

log()  { echo "[$(date -Is)] $*" | tee -a "$LOG" ; }
ntfy() { # title priority message
  curl -sm 10 -H "Authorization: Bearer ${NTFY_TOKEN:-}" \
    -H "Title: $1" -H "Priority: $2" -H "Tags: ${3:-gear}" \
    -d "$4" "$NTFY_URL" >/dev/null 2>&1 || log "ntfy send failed: $1"
}
# run a command on the NAS as root (password over stdin, never argv)
nas_sudo() { printf '%s\n' "$NAS_SUDO_PASSWORD" | "${NAS_SSH[@]}" "sudo -S -p '' $*" ; }
nas_run()  { "${NAS_SSH[@]}" "$*" ; }

fail() { # step message
  log "FAIL: $1"
  ntfy "Window maint: FAILED at $1" high rotating_light "$2

Fleet left in last-good state; inspect before the next window. Log: $LOG on mini."
  exit 1
}

log "=== window maintenance start (DRY_RUN=$DRY_RUN) ==="
[ "$DRY_RUN" = "1" ] || ntfy "Window maint: START" default gear \
  "unpackerr wedge clear + rclone retune. Two gated phases, will report each."

# =============================================================================
# PRE-FLIGHT
# =============================================================================
BEFORE_COUNT=$(nas_sudo "timeout 15 $DOCKER ps --format '{{.Names}}' | wc -l" 2>/dev/null | tr -d '[:space:]')
log "pre-flight: $BEFORE_COUNT containers running (expect ~$EXPECT_CONTAINERS)"
[ "${BEFORE_COUNT:-0}" -ge 1 ] || fail "pre-flight" "NAS docker not responding (got '$BEFORE_COUNT' containers)."

UNPACKERR_STATUS=$(nas_sudo "timeout 15 $DOCKER inspect unpackerr --format '{{.State.Status}}'" 2>/dev/null | tr -d '[:space:]')
log "pre-flight: unpackerr status=$UNPACKERR_STATUS"

if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN: verifying the retuned mount script + compose are staged on the NAS…"
  nas_run "grep -q 'vfs-cache-mode full' /volume1/scripts/media/rclone-seedbox-mount.sh" \
    && log "  OK: mount script has vfs-cache-mode full" || fail "dry-run: mount script" "retune not staged on NAS."
  nas_run "grep -q 5656 $COMPOSE_DIR/docker-compose.yml" \
    && log "  OK: compose has the unpackerr healthcheck" || fail "dry-run: compose" "healthcheck not staged on NAS."
  ntfy "Window maint: DRY-RUN OK" default white_check_mark \
    "Pre-flight + staged-config checks passed; ssh/sudo/ntfy paths work. Real run will fire in the window."
  log "=== DRY_RUN complete — no changes made ==="
  exit 0
fi

# =============================================================================
# PHASE A — clear the unpackerr wedge, apply the healthcheck
# =============================================================================
log "PHASE A: restarting dockerd on the NAS (pkg-ContainerManager-dockerd)…"
nas_sudo "systemctl restart pkg-ContainerManager-dockerd.service" 2>&1 | tee -a "$LOG"

# target the count we actually saw at pre-flight (tolerate 1 transient), not a
# hardcoded number that drifts as the stack grows.
TARGET=$(( BEFORE_COUNT>1 ? BEFORE_COUNT-1 : 1 ))
log "PHASE A: waiting for dockerd + containers to return (>= $TARGET, up to 5 min)…"
ok=0
for i in $(seq 1 30); do
  sleep 10
  c=$(nas_sudo "timeout 15 $DOCKER ps --format '{{.Names}}' | wc -l" 2>/dev/null | tr -d '[:space:]')
  log "  attempt $i: $c containers up"
  if [ "${c:-0}" -ge "$TARGET" ]; then ok=1; break; fi
done
[ "$ok" = "1" ] || fail "phase-A dockerd restart" "Only ${c:-0} containers came back (wanted >= $TARGET of $BEFORE_COUNT) after the dockerd restart."

log "PHASE A: applying compose (recreates unpackerr with healthcheck+webserver)…"
nas_sudo "cd $COMPOSE_DIR && $DOCKER compose up -d" 2>&1 | tee -a "$LOG"

log "PHASE A: waiting for unpackerr to report healthy (up to 3 min)…"
ok=0
for i in $(seq 1 18); do
  sleep 10
  h=$(nas_sudo "timeout 15 $DOCKER inspect unpackerr --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}nohealth{{end}}'" 2>/dev/null | tr -d '[:space:]')
  log "  attempt $i: unpackerr health=$h"
  [ "$h" = "healthy" ] && { ok=1; break; }
done
[ "$ok" = "1" ] || fail "phase-A unpackerr health" "unpackerr did not reach 'healthy' (last=$h). Webserver/healthcheck may need tuning."

# any unhealthy/exited container after the bounce?
BAD=$(nas_sudo "timeout 20 $DOCKER ps -a --format '{{.Names}} {{.Status}}' | grep -viE 'Up ' | grep -v '_run_' | head" 2>/dev/null)
[ -z "$BAD" ] || fail "phase-A container health" "Containers not healthy after restart:\n$BAD"
log "PHASE A: complete — all containers up, unpackerr healthy"
ntfy "Window maint: PHASE A OK" default white_check_mark \
  "unpackerr wedge cleared, healthcheck live, all $EXPECT_CONTAINERS containers healthy."

# =============================================================================
# PHASE B — remount rclone with the retuned flags, rebind the *arrs
# =============================================================================
log "PHASE B: lazy-unmounting the current rclone mount…"
nas_sudo "fusermount -uz $MOUNTPOINT 2>/dev/null || umount -l $MOUNTPOINT 2>/dev/null || true"
sleep 3
log "PHASE B: remounting with retuned flags (mount script)…"
nas_sudo "/volume1/scripts/media/rclone-seedbox-mount.sh" 2>&1 | tee -a "$LOG"

log "PHASE B: verifying the new mount lists + cache-mode is full (up to 2 min)…"
ok=0
for i in $(seq 1 12); do
  sleep 10
  listed=$(nas_sudo "timeout 15 ls $MOUNTPOINT/tv 2>/dev/null | head -1" 2>/dev/null | tr -d '[:space:]')
  [ -n "$listed" ] && { ok=1; break; }
  log "  attempt $i: mount not yet listable"
done
[ "$ok" = "1" ] || fail "phase-B remount" "Retuned mount did not become listable — imports would stall. CHECK NOW."
CACHEMODE=$(nas_sudo "grep -oE 'vfs-cache-mode [a-z]+' /proc/\$(pgrep -f 'rclone mount' | head -1)/cmdline 2>/dev/null || cat /proc/\$(pgrep -f 'rclone mount'|head -1)/cmdline 2>/dev/null | tr '\0' ' ' | grep -oE 'vfs-cache-mode [a-z]+'" 2>/dev/null)
log "PHASE B: running rclone cmdline cache-mode: ${CACHEMODE:-unknown}"

log "PHASE B: restarting download-touching containers to bind the fresh mount…"
nas_sudo "cd $COMPOSE_DIR && $DOCKER compose restart sonarr radarr lidarr readarr unpackerr" 2>&1 | tee -a "$LOG"
sleep 15

# verify a container actually SEES the mount content (end-to-end)
INSIDE=$(nas_sudo "timeout 20 $DOCKER exec sonarr sh -c 'ls /seedbox/tv 2>/dev/null | head -1'" 2>/dev/null | tr -d '[:space:]')
[ -n "$INSIDE" ] || fail "phase-B in-container mount" "sonarr cannot see /seedbox/tv after remount — the bind is stale. CHECK NOW."
log "PHASE B: complete — sonarr sees the mount ($INSIDE…)"

# =============================================================================
# WRAP-UP
# =============================================================================
FINAL=$(nas_sudo "timeout 20 $DOCKER ps --format '{{.Names}}' | wc -l" 2>/dev/null | tr -d '[:space:]')
UHEALTH=$(nas_sudo "timeout 15 $DOCKER inspect unpackerr --format '{{.State.Health.Status}}'" 2>/dev/null | tr -d '[:space:]')
log "wrap-up: $FINAL containers up, unpackerr=$UHEALTH, mount cache-mode=${CACHEMODE:-?}"
ntfy "Window maint: DONE ✓" default white_check_mark \
  "Phase A (unpackerr healthcheck live) + Phase B (rclone retuned to vfs-cache full) complete. $FINAL containers up, unpackerr=$UHEALTH. Run the verification sweep to confirm."

# self-clean: disable the one-shot timer so it can't re-fire
if systemctl list-unit-files 2>/dev/null | grep -q '^media-window-maint.timer'; then
  sudo systemctl disable --now media-window-maint.timer 2>/dev/null \
    && log "disabled media-window-maint.timer (one-shot done)" || log "note: could not disable timer (do it manually)"
fi
log "=== window maintenance complete ==="
