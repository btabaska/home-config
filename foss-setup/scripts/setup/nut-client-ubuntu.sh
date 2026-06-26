#!/usr/bin/env bash
#
# nut-client-ubuntu.sh
# Configure the Ubuntu box (Mac mini) as a NUT *netclient* that listens to the
# Synology NAS's UPS over the network and shuts down gracefully on a long outage.
#
# Architecture (Section 7 power resilience):
#   UPS --USB--> DS920+ (DSM = NUT *server*, "netserver")  <--network--  Ubuntu (this box, "netclient")
#   The Dream Wall is also on the UPS battery; it just rides through outages.
#   DSM owns the UPS and does its own graceful shutdown; this box only *monitors*
#   the NAS's UPS status and shuts itself down before the battery dies.
#
# Prereqs ON THE SYNOLOGY (do this first, in DSM):
#   Control Panel -> Hardware & Power -> UPS:
#     * Enable UPS support, type = USB UPS
#     * Enable "network UPS server"
#     * "Permitted DiskStation Devices" -> add THIS box's static IP
#   Defaults DSM exposes to clients: UPS name = "ups", user = "monuser",
#   password = "secret". (Verify via SSH on DSM: `cat /etc/ups/upsd.users` and
#   `cat /etc/ups/ups.conf`.)
#
# Docs:
#   - NUT user manual:   https://networkupstools.org/docs/user-manual.chunked/
#   - nut.conf(5):       https://networkupstools.org/docs/man/nut.conf.html
#   - upsmon.conf(5):    https://networkupstools.org/docs/man/upsmon.conf.html
#   - Synology as NUT primary (community): https://www.johnra.me/2024/05/16/synology-ups-as-nut-primary/
#
# Idempotent: re-running re-writes the managed config blocks and restarts the
# monitor only if something changed. Run with sudo.
#
# Usage:
#   sudo NAS_IP=192.168.1.7 ./nut-client-ubuntu.sh
#   sudo NAS_IP=192.168.1.7 UPS_NAME=ups UPS_USER=monuser UPS_PASS=secret ./nut-client-ubuntu.sh
set -euo pipefail

NAS_IP="${NAS_IP:-}"
UPS_NAME="${UPS_NAME:-ups}"            # Synology default UPS name
UPS_USER="${UPS_USER:-monuser}"        # Synology default monitor user
UPS_PASS="${UPS_PASS:-secret}"         # Synology default monitor password
MINSUPPLIES="${MINSUPPLIES:-1}"

NUT_CONF="/etc/nut/nut.conf"
UPSMON_CONF="/etc/nut/upsmon.conf"

log()  { printf '\033[1;35m[nut]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[nut][!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[nut][x]\033[0m %s\n' "$*" >&2; exit 1; }

[[ "${EUID}" -eq 0 ]] || die "Run as root or with sudo."
[[ -n "${NAS_IP}" ]]  || die "Set NAS_IP=<Synology IP> (the NUT server). e.g. sudo NAS_IP=192.168.1.7 $0"

install_pkg() {
  if dpkg -s nut-client >/dev/null 2>&1; then
    log "nut-client already installed."
  else
    log "Installing nut-client."
    apt-get update -y
    apt-get install -y nut-client
  fi
}

# Replace a "KEY=VALUE" line in a file (key-anchored), or append if absent.
set_kv() {
  local file="$1" key="$2" val="$3"
  touch "${file}"
  if grep -qE "^[#[:space:]]*${key}=" "${file}"; then
    sed -i -E "s|^[#[:space:]]*${key}=.*|${key}=${val}|" "${file}"
  else
    printf '%s=%s\n' "${key}" "${val}" >>"${file}"
  fi
}

configure_mode() {
  # netclient: this box runs only upsmon, monitoring a remote upsd (the NAS).
  log "Setting MODE=netclient in ${NUT_CONF}"
  set_kv "${NUT_CONF}" "MODE" "netclient"
}

configure_upsmon() {
  log "Writing managed MONITOR block to ${UPSMON_CONF} (target: ${UPS_NAME}@${NAS_IP})"
  [[ -f "${UPSMON_CONF}.orig" ]] || { [[ -f "${UPSMON_CONF}" ]] && cp -a "${UPSMON_CONF}" "${UPSMON_CONF}.orig"; }

  local begin="# >>> nut-client-ubuntu.sh (managed) >>>"
  local end="# <<< nut-client-ubuntu.sh (managed) <<<"
  # type=secondary: the NAS (primary) shuts down LAST; this box shuts down when
  # upsmon sees the UPS go ONBATT + LOWBATT (or the NAS drops the connection).
  local block
  block="$(cat <<EOF
${begin}
MONITOR ${UPS_NAME}@${NAS_IP} 1 ${UPS_USER} ${UPS_PASS} secondary
MINSUPPLIES ${MINSUPPLIES}
SHUTDOWNCMD "/sbin/shutdown -h +0"
POWERDOWNFLAG /etc/killpower
${end}
EOF
)"

  touch "${UPSMON_CONF}"
  if grep -qF "${begin}" "${UPSMON_CONF}"; then
    # Replace the existing managed block in place.
    local tmp; tmp="$(mktemp)"
    awk -v b="${begin}" -v e="${end}" -v repl="${block}" '
      $0==b {print repl; skip=1; next}
      $0==e {skip=0; next}
      skip!=1 {print}
    ' "${UPSMON_CONF}" >"${tmp}"
    mv "${tmp}" "${UPSMON_CONF}"
  else
    printf '\n%s\n' "${block}" >>"${UPSMON_CONF}"
  fi
  chmod 640 "${UPSMON_CONF}" 2>/dev/null || true
}

restart_monitor() {
  # Service name differs across NUT packaging; try the modern split unit first.
  log "Restarting the NUT monitor service."
  if systemctl list-unit-files | grep -q '^nut-monitor\.service'; then
    systemctl enable --now nut-monitor.service
    systemctl restart nut-monitor.service
  elif systemctl list-unit-files | grep -q '^nut-client\.service'; then
    systemctl enable --now nut-client.service
    systemctl restart nut-client.service
  else
    warn "No nut-monitor/nut-client unit found; trying 'upsmon -c reload'."
    upsmon -c reload || warn "Could not reload upsmon; check 'journalctl -u nut-monitor'."
  fi
}

verify() {
  log "Verifying connection to ${UPS_NAME}@${NAS_IP}..."
  if command -v upsc >/dev/null 2>&1; then
    if upsc "${UPS_NAME}@${NAS_IP}" >/dev/null 2>&1; then
      log "OK — UPS reachable. Key values:"
      upsc "${UPS_NAME}@${NAS_IP}" 2>/dev/null | grep -E '^(ups\.status|battery\.charge|ups\.load)' || true
    else
      warn "Could not query ${UPS_NAME}@${NAS_IP}."
      warn "Check: (1) DSM 'network UPS server' enabled, (2) this box's IP is in"
      warn "       'Permitted DiskStation Devices', (3) UPS_NAME/USER/PASS match"
      warn "       DSM's /etc/ups/{ups.conf,upsd.users}, (4) no firewall blocks TCP 3493."
    fi
  fi
  log "Monitor status:"
  systemctl --no-pager --full status nut-monitor.service 2>/dev/null \
    || systemctl --no-pager --full status nut-client.service 2>/dev/null || true
}

main() {
  install_pkg
  configure_mode
  configure_upsmon
  restart_monitor
  verify
  log "Done. This box now shuts down gracefully when the NAS's UPS hits low battery."
}

main "$@"
