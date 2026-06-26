#!/usr/bin/env bash
#
# wake-rig.sh
# Send a Wake-on-LAN magic packet from the Mac mini (Ubuntu) or a laptop to wake
# the CachyOS rig on the LAN. The rig must already have WoL armed in BIOS + OS
# (see enable-wol-cachyos.sh) and must be on the same broadcast domain (same
# Trusted VLAN). WoL is L2 broadcast: it does NOT route across subnets/VLANs
# unless your router/switch is set up to forward directed broadcasts.
#
# Usage:
#   export RIG_MAC=aa:bb:cc:dd:ee:ff   # the rig NIC MAC (printed by enable-wol-cachyos.sh)
#   ./wake-rig.sh                      # send magic packet
#   RIG_MAC=aa:bb:... ./wake-rig.sh    # one-shot override
#
# Optional:
#   RIG_BCAST=192.168.10.255           # subnet broadcast addr (improves reliability)
#
# Docs:
#   - Arch Wiki Wake-on-LAN:      https://wiki.archlinux.org/title/Wake-on-LAN
#   - Ubuntu WakeOnLan community: https://help.ubuntu.com/community/WakeOnLan
#
# Idempotent + safe: set -euo pipefail.

set -euo pipefail

log() { printf '[wake] %s\n' "$*"; }
die() { printf '[wake] ERROR: %s\n' "$*" >&2; exit 1; }

RIG_MAC="${RIG_MAC:-}"
RIG_BCAST="${RIG_BCAST:-255.255.255.255}"

[[ -n "${RIG_MAC}" ]] || die "Set RIG_MAC=aa:bb:cc:dd:ee:ff (the rig's wired NIC MAC)."

# Basic MAC sanity check.
[[ "${RIG_MAC}" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]] \
  || die "RIG_MAC '${RIG_MAC}' is not a valid colon-separated MAC."

# Pick whichever WoL sender tool is installed. On Ubuntu:  apt install wakeonlan
# (or 'etherwake'). On Arch/Mac (brew):  pacman -S wol  /  brew install wakeonlan.
if command -v wakeonlan >/dev/null 2>&1; then
  log "Sending magic packet via wakeonlan to ${RIG_MAC} (bcast ${RIG_BCAST})"
  wakeonlan -i "${RIG_BCAST}" "${RIG_MAC}"
elif command -v wol >/dev/null 2>&1; then
  log "Sending magic packet via wol to ${RIG_MAC}"
  wol "${RIG_MAC}"
elif command -v etherwake >/dev/null 2>&1; then
  # etherwake needs root and an interface; it crafts a raw L2 frame.
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
log "Verify it is up:  ping <rig-ip>   or   tailscale ping <rig-name>"
