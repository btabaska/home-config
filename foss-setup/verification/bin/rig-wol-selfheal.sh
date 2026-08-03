#!/usr/bin/env bash
# rig-wol-selfheal.sh — fast-tier rig-down auto-recovery (fix-63 / SM54).
#
# WHY: the rig runs 24/7, so rig-down is an incident. The fast tier (every 10
# min) already DETECTS and pages rig-down within ~10 min, but the only WoL
# RECOVERY logic lived in the DAILY verification cycle (llm-triage.sh) — so a rig
# that dropped just after a daily run got no automated wake for up to ~24h. This
# script moves the recovery action into the fast tier: it fires a magic packet
# the moment the fast tier notices the rig is unreachable, and escalates with an
# hourly re-page while the rig stays down (SM54 also asked for a >1h re-page
# instead of first-page-then-dedup-silence).
#
# Wired as an ExecStartPost (- prefixed => never fails the unit) on
# verification-fast.service, so it runs every ~10 min alongside the fast sweep.
# Idempotent + rate-limited via a small state file; safe to run every cycle.
set -uo pipefail

ENV_FILE="${VERIFICATION_ENV_FILE:-/etc/verification/env}"
[ -r "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a

STATE_DIR="${VERIFICATION_STATE_DIR:-/var/lib/verification}"
RIG_HOST="${RIG_HOST:-192.168.10.12}"
RIG_MAC="${RIG_MAC:-50:eb:f6:b5:82:c6}"
RIG_BCAST="${RIG_BCAST:-192.168.10.255}"
PROBE_TIMEOUT="${PROBE_TIMEOUT:-4}"
REPAGE_SECS="${RIG_REPAGE_SECS:-3600}"
# ntfy for the escalation re-page (self-hosted; rig-down, mini is up so this works)
NTFY_URL="${NTFY_URL:-http://127.0.0.1:8080/homelab-alerts}"
NTFY_ESCALATE_URL="${NTFY_ESCALATE_URL:-${NTFY_URL%/*}/homelab-alerts}"
NTFY_TOKEN="${NTFY_TOKEN:-}"

STATE_FILE="${STATE_DIR}/rig-wol-selfheal.state"
mkdir -p "$STATE_DIR"
now=$(date +%s)

get() { sed -n "s/^$1=//p" "$STATE_FILE" 2>/dev/null | tail -1; }
status=$(get status);         status="${status:-up}"
down_since=$(get down_since); down_since="${down_since:-0}"
last_page=$(get last_page);   last_page="${last_page:-0}"
write_state() { { echo "status=$1"; echo "down_since=$2"; echo "last_page=$3"; } > "$STATE_FILE"; }

rig_up() {
  [ "${RIG_SELFHEAL_FORCE_DOWN:-0}" = "1" ] && return 1  # test hook
  # SSH port is the liveness signal (host answering + reachable over LAN).
  timeout "$PROBE_TIMEOUT" bash -c "exec 3<>/dev/tcp/${RIG_HOST}/22" 2>/dev/null
}

send_wol() {
  # Prefer the operator's wake-rig helper if present (game-08); else wakeonlan.
  if [ -x "$HOME/wake-rig.sh" ]; then
    RIG_MAC="$RIG_MAC" bash "$HOME/wake-rig.sh" >/dev/null 2>&1 || true
  elif command -v wakeonlan >/dev/null 2>&1; then
    wakeonlan -i "$RIG_BCAST" "$RIG_MAC" >/dev/null 2>&1 || true
  else
    echo "rig-wol-selfheal: no WoL tool (wake-rig.sh / wakeonlan) available" >&2
  fi
}

escalate() { # message
  [ -z "$NTFY_TOKEN" ] && return 0
  curl -fsS -m 10 --retry 2 -H "Authorization: Bearer ${NTFY_TOKEN}" \
    -H "Title: rig still down — auto-recovery not converging" -H "Priority: high" \
    -H "Tags: rotating_light,rig" -d "$1" "$NTFY_ESCALATE_URL" -o /dev/null \
    || echo "rig-wol-selfheal: escalation page failed (non-fatal)" >&2
}

if rig_up; then
  [ "$status" = "down" ] && echo "rig-wol-selfheal: rig back up" >&2
  write_state up 0 0
  exit 0
fi

# rig is down
if [ "$status" != "down" ]; then
  down_since="$now"
  echo "rig-wol-selfheal: rig unreachable (${RIG_HOST}:22) — firing WoL" >&2
  send_wol
  write_state down "$down_since" 0
  exit 0
fi

# still down on a subsequent cycle: keep nudging + escalate hourly
send_wol
if [ $((now - last_page)) -ge "$REPAGE_SECS" ]; then
  dur=$(( (now - down_since) / 60 ))
  escalate "rig has been unreachable for ~${dur} min despite repeated WoL attempts. This is a 24/7-host incident — likely a physical fault (PSU/breaker/hung board or the OS-NVMe PCIe link). Go check it."
  last_page="$now"
  echo "rig-wol-selfheal: re-paged (rig down ~$(( (now - down_since)/60 ))m)" >&2
fi
write_state down "$down_since" "$last_page"
exit 0
