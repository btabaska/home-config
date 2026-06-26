#!/usr/bin/env bash
#
# enable-wol-cachyos.sh
# Persistently enable Wake-on-LAN (magic packet) on the CachyOS rig's wired NIC.
#
# WoL has two halves: (1) BIOS/UEFI must allow "Wake on PCIe/LAN" / "Power On By
# PCI-E" AND disable deep ErP/EuP power-off that cuts power to the NIC; (2) the OS
# must arm the NIC with `ethtool -s <nic> wol g` on every boot. `ethtool` settings
# do NOT survive a reboot on most systems, so we install a templated systemd unit
# that re-arms the NIC at boot.
#
# Docs:
#   - Arch Wiki Wake-on-LAN:        https://wiki.archlinux.org/title/Wake-on-LAN
#   - Ubuntu WakeOnLan community:   https://help.ubuntu.com/community/WakeOnLan
#
# Idempotent: safe to re-run. set -euo pipefail for strict error handling.

set -euo pipefail

# ---- config ---------------------------------------------------------------
# Override the NIC by exporting WOL_NIC=enpXsY before running. If unset we try
# to autodetect the primary wired interface (the one with the default route).
WOL_NIC="${WOL_NIC:-}"

log()  { printf '[wol] %s\n' "$*"; }
die()  { printf '[wol] ERROR: %s\n' "$*" >&2; exit 1; }

[[ ${EUID} -eq 0 ]] || die "Run as root (sudo $0)."

command -v ethtool >/dev/null 2>&1 || die "ethtool not found. Install it: pacman -S ethtool"

# ---- detect NIC -----------------------------------------------------------
if [[ -z "${WOL_NIC}" ]]; then
  WOL_NIC="$(ip -o route show default 2>/dev/null | awk '{print $5; exit}')" || true
  [[ -n "${WOL_NIC}" ]] || die "Could not autodetect NIC. Re-run with WOL_NIC=<iface> (see: ip link)."
fi
[[ -d "/sys/class/net/${WOL_NIC}" ]] || die "Interface '${WOL_NIC}' does not exist (check: ip link)."
log "Target NIC: ${WOL_NIC}"

# ---- capability check -----------------------------------------------------
# 'Supports Wake-on:' must contain 'g' (magic packet) for this to work at all.
supports="$(ethtool "${WOL_NIC}" 2>/dev/null | awk -F': ' '/Supports Wake-on/{print $2}')" || true
log "Supports Wake-on: ${supports:-unknown}"
case "${supports}" in
  *g*) : ;;  # good
  *)   log "WARNING: NIC does not advertise magic-packet (g) support. Realtek r8169 NICs"
       log "         sometimes need the proprietary r8168 driver. Continuing anyway." ;;
esac

# ---- arm now --------------------------------------------------------------
current="$(ethtool "${WOL_NIC}" 2>/dev/null | awk -F': ' '/Wake-on/ && !/Supports/{print $2}')" || true
if [[ "${current}" == "g" ]]; then
  log "WoL already armed (Wake-on: g). No change needed."
else
  log "Arming WoL now: ethtool -s ${WOL_NIC} wol g"
  ethtool -s "${WOL_NIC}" wol g
fi

# ---- persist via systemd template unit ------------------------------------
UNIT_PATH="/etc/systemd/system/wol@.service"
if [[ ! -f "${UNIT_PATH}" ]]; then
  log "Writing systemd template unit ${UNIT_PATH}"
  cat > "${UNIT_PATH}" <<'EOF'
[Unit]
Description=Enable Wake-on-LAN (magic packet) on %i
# Run after the device exists; oneshot re-arms the NIC at every boot.
Requires=network.target
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/ethtool -s %i wol g

[Install]
WantedBy=multi-user.target
EOF
else
  log "systemd template unit already present."
fi

systemctl daemon-reload
if systemctl is-enabled "wol@${WOL_NIC}.service" >/dev/null 2>&1; then
  log "wol@${WOL_NIC}.service already enabled."
else
  log "Enabling wol@${WOL_NIC}.service"
  systemctl enable "wol@${WOL_NIC}.service"
fi
systemctl start "wol@${WOL_NIC}.service" || true

# ---- report MAC + verification --------------------------------------------
mac="$(cat "/sys/class/net/${WOL_NIC}/address" 2>/dev/null || echo unknown)"
log "Done. NIC ${WOL_NIC} MAC = ${mac}"
log "Record this MAC for wake-rig.sh:  export RIG_MAC=${mac}"
log "Verify after reboot:  ethtool ${WOL_NIC} | grep -i 'Wake-on'   (want: Wake-on: g)"

# NOTE: If you use NetworkManager and it manages this NIC, it can override the
# above. In that case ALSO set it in the connection profile so it survives
# reconnects:
#   nmcli connection modify "<Connection Name>" 802-3-ethernet.wake-on-lan magic
# See: https://help.ubuntu.com/community/WakeOnLan
