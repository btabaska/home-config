#!/usr/bin/env bash
# Rig is 24/7 since 2026-07 — this is RECOVERY tooling (power outage / accidental shutdown), not workflow.
#
# wake-rig.sh
# Send a Wake-on-LAN magic packet to the CachyOS rig on the Trusted VLAN.
#
# Config (no shell exports needed):
#   configs/gaming/rig-wol.env  — RIG_MAC (committed fleet constant)
#   RIG_BCAST is auto-detected from this machine's default-route subnet.
#
# Usage (from repo, any LAN device with wakeonlan installed):
#   ./scripts/gaming/wake-rig.sh
#
# From anywhere on the tailnet (mini is always on the same L2 segment as the rig):
#   ./scripts/gaming/wake-rig-via-mini.sh
#   ssh mini 'bash ~/wake-rig.sh'
#
# Overrides (optional):
#   RIG_MAC=aa:bb:... RIG_BCAST=192.168.10.255 ./wake-rig.sh
#   WOL_CONFIG=/path/to/rig-wol.env ./wake-rig.sh
#
# Docs:
#   - Arch Wiki Wake-on-LAN:      https://wiki.archlinux.org/title/Wake-on-LAN
#   - Ubuntu WakeOnLan community: https://help.ubuntu.com/community/WakeOnLan
#
# Idempotent + safe: set -euo pipefail.

set -euo pipefail

log() { printf '[wake] %s\n' "$*"; }
die() { printf '[wake] ERROR: %s\n' "$*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- load fleet config ---------------------------------------------------------
load_wol_config() {
  local candidate
  if [[ -n "${WOL_CONFIG:-}" && -f "${WOL_CONFIG}" ]]; then
    # shellcheck source=/dev/null
    source "${WOL_CONFIG}"
    return 0
  fi
  for candidate in \
    "${SCRIPT_DIR}/rig-wol.env" \
    "${SCRIPT_DIR}/../../configs/gaming/rig-wol.env" \
    "${HOME}/.config/homelab/rig-wol.env"; do
    if [[ -f "${candidate}" ]]; then
      # shellcheck source=/dev/null
      source "${candidate}"
      return 0
    fi
  done
  return 1
}

if [[ -z "${RIG_MAC:-}" ]]; then
  load_wol_config || die "RIG_MAC not set. Add configs/gaming/rig-wol.env or export RIG_MAC."
fi

# --- auto-detect subnet broadcast from default route ---------------------------
detect_bcast() {
  local iface cidr ip prefix
  if command -v ip >/dev/null 2>&1; then
    iface="$(ip -o route show default 2>/dev/null | awk '{print $5; exit}')" || true
    [[ -n "${iface}" ]] || return 1
    cidr="$(ip -o -4 addr show dev "${iface}" 2>/dev/null | awk '{print $4; exit}')" || true
    [[ -n "${cidr}" && "${cidr}" == */* ]] || return 1
    if command -v python3 >/dev/null 2>&1; then
      python3 - <<PY
import ipaddress
print(ipaddress.ip_network("${cidr}", strict=False).broadcast_address)
PY
      return 0
    fi
  elif [[ "$(uname -s)" == Darwin ]]; then
    iface="$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}')" || true
    [[ -n "${iface}" ]] || return 1
    ip="$(ifconfig "${iface}" 2>/dev/null | awk '/inet / {print $2; exit}')" || true
    [[ -n "${ip}" ]] || return 1
    # Homelab Trusted VLAN is /24; good default when python/ipcalc unavailable.
    printf '%s.255\n' "${ip%.*}"
    return 0
  fi
  return 1
}

RIG_BCAST="${RIG_BCAST:-}"
if [[ -z "${RIG_BCAST}" ]]; then
  RIG_BCAST="$(detect_bcast 2>/dev/null || echo 255.255.255.255)"
fi

[[ -n "${RIG_MAC}" ]] || die "RIG_MAC is empty in config."

[[ "${RIG_MAC}" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]] \
  || die "RIG_MAC '${RIG_MAC}' is not a valid colon-separated MAC."

# --- send magic packet ---------------------------------------------------------
if command -v wakeonlan >/dev/null 2>&1; then
  log "Sending magic packet via wakeonlan to ${RIG_MAC} (bcast ${RIG_BCAST})"
  wakeonlan -i "${RIG_BCAST}" "${RIG_MAC}"
elif command -v wol >/dev/null 2>&1; then
  log "Sending magic packet via wol to ${RIG_MAC}"
  wol "${RIG_MAC}"
elif command -v etherwake >/dev/null 2>&1; then
  IFACE="$(ip -o route show default 2>/dev/null | awk '{print $5; exit}')"
  log "Sending magic packet via etherwake on ${IFACE} to ${RIG_MAC}"
  sudo etherwake -i "${IFACE}" "${RIG_MAC}"
else
  die "No WoL tool found. Install one:
       Ubuntu:  sudo apt install wakeonlan
       Arch:    sudo pacman -S wol
       macOS:   brew install wakeonlan"
fi

log "Magic packet sent. The rig should boot within ~30-60s."
log "Verify:  tailscale ping cachyos   or   ssh rig 'hostname'"
