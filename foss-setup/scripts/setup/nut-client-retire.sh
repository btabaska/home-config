#!/usr/bin/env bash
#
# nut-client-retire.sh
# Retire the NUT *netclient* (upsmon) on this box and stop the dead-poll spam.
#
# WHY THIS EXISTS (quality-gate fix-31 / findings H1, H29, M59)
# ------------------------------------------------------------
# nut-client-ubuntu.sh configured the Mac mini as a NUT netclient that monitors a
# UPS attached to the Synology NAS (upsd@192.168.10.4:3493). But:
#   * no UPS is physically attached to the NAS (no /dev/ups*, no power_supply),
#   * DSM UPS support + "network UPS server" are OFF, so the NAS never runs upsd.
# mini's upsmon therefore retried every ~5s for 7+ days — ~120k "Connection
# refused" journal errors and 4G+ of journal bloat — while providing ZERO
# power-loss protection. It only *looked* like protection was "degraded".
#
# Operator decision (2026-07-17): no UPS budget right now — this folds into the
# deferred glue-01 (UPS/NUT power resilience). Retire the dead client rather than
# pretend it protects anything, and stop the journal spam.
#
# REVERSIBLE. To bring UPS monitoring back once a UPS is wired to the NAS and DSM
# UPS support + network UPS server are enabled (with this box's IP permitted):
#     sudo NUT_REENABLE=1 NAS_IP=192.168.10.4 ./nut-client-ubuntu.sh
# That path unmasks the unit, restores MODE=netclient, and rewrites the MONITOR
# block. This retire script and that re-enable path are exact inverses.
#
# Idempotent: re-running leaves an already-retired client retired. Run with sudo.
set -euo pipefail

NUT_CONF="/etc/nut/nut.conf"
UPSMON_CONF="/etc/nut/upsmon.conf"
UNIT="nut-monitor.service"
BEGIN="# >>> nut-client-ubuntu.sh (managed) >>>"
END="# <<< nut-client-ubuntu.sh (managed) <<<"

log()  { printf '\033[1;35m[nut-retire]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[nut-retire][!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[nut-retire][x]\033[0m %s\n' "$*" >&2; exit 1; }

[[ "${EUID}" -eq 0 ]] || die "Run as root or with sudo."

# 1) Stop + disable + mask the unit. Masking is the hard guard: a masked unit
#    cannot be started by an accidental `systemctl start`, a dependency, or a
#    stray re-run of nut-client-ubuntu.sh (which would fail on the masked unit).
if systemctl list-unit-files "${UNIT}" >/dev/null 2>&1 && \
   systemctl list-unit-files "${UNIT}" 2>/dev/null | grep -q "${UNIT%.service}"; then
  if [[ "$(systemctl is-active "${UNIT}" 2>/dev/null || true)" == "active" ]]; then
    log "Stopping ${UNIT}."
    systemctl stop "${UNIT}" || true
  fi
  if [[ "$(systemctl is-enabled "${UNIT}" 2>/dev/null || true)" != "masked" ]]; then
    log "Disabling + masking ${UNIT}."
    systemctl disable "${UNIT}" 2>/dev/null || true
    systemctl mask "${UNIT}"
  else
    log "${UNIT} already masked."
  fi
else
  log "${UNIT} not present — nothing to mask."
fi

# 2) Neutralize the config (defense in depth + documents intent). Even if the
#    unit is ever unmasked by hand, MODE=none + a commented MONITOR block means
#    upsmon has nothing to poll and will not spam.
if [[ -f "${NUT_CONF}" ]] && grep -qE '^\s*MODE=netclient' "${NUT_CONF}"; then
  log "Setting MODE=none in ${NUT_CONF} (was netclient)."
  sed -i -E 's|^\s*MODE=netclient.*|MODE=none|' "${NUT_CONF}"
else
  log "${NUT_CONF} MODE already not netclient."
fi

if [[ -f "${UPSMON_CONF}" ]] && grep -qF "${BEGIN}" "${UPSMON_CONF}"; then
  # Comment every non-marker line inside the managed block, if not already done.
  if awk -v b="${BEGIN}" -v e="${END}" '
        $0==b {inblk=1; next} $0==e {inblk=0; next}
        inblk && $0 !~ /^#\[retired\]/ && $0 !~ /^[[:space:]]*$/ {found=1}
        END {exit found?0:1}' "${UPSMON_CONF}"; then
    log "Commenting the managed MONITOR block in ${UPSMON_CONF}."
    tmp="$(mktemp)"
    awk -v b="${BEGIN}" -v e="${END}" '
      $0==b {print; inblk=1; next}
      $0==e {print; inblk=0; next}
      inblk && $0 !~ /^#\[retired\]/ && $0 !~ /^[[:space:]]*$/ {print "#[retired] " $0; next}
      {print}
    ' "${UPSMON_CONF}" >"${tmp}"
    cat "${tmp}" >"${UPSMON_CONF}"   # preserve perms/owner (root:nut 640)
    rm -f "${tmp}"
  else
    log "Managed MONITOR block already commented."
  fi
else
  log "No managed MONITOR block in ${UPSMON_CONF} — nothing to comment."
fi

log "Done. nut-monitor is retired (masked + inactive); no UPS is attached."
log "Re-enable path: sudo NUT_REENABLE=1 NAS_IP=192.168.10.4 ./nut-client-ubuntu.sh"
