#!/usr/bin/env bash
#
# apply-journald-cap.sh — install the fleet journald size cap on THIS host and
# enforce it now. Idempotent. Run as root on the target host (mini or rig).
#
# WHY (quality-gate fix-31): journald had no size cap, so mini's dead upsmon
# client (retired in the same fix) grew the persistent journal to 4.1G. This
# bounds SystemMaxUse so no runaway logger can eat the disk. See the sibling
# 10-size-cap.conf and wiki/docs/runbooks/power-resilience.md.
#
# Usage (on the host):   sudo ./apply-journald-cap.sh
# From a workstation:    ssh mini 'sudo bash -s' < apply-journald-cap.sh
set -euo pipefail

DEST="/etc/systemd/journald.conf.d/10-size-cap.conf"
# ${BASH_SOURCE[0]:-$0}: BASH_SOURCE is unbound (not just empty) under `set -u`
# when the script is piped in via `ssh host 'sudo bash -s'` — default to $0 so
# we degrade to the embedded copy instead of dying on the unbound reference.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
SRC="${DIR:+${DIR}/10-size-cap.conf}"

log() { printf '\033[1;36m[journald-cap]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[journald-cap][x]\033[0m %s\n' "$*" >&2; exit 1; }

[[ "${EUID}" -eq 0 ]] || die "Run as root or with sudo."

install -d -m 0755 /etc/systemd/journald.conf.d

# Prefer the canonical sibling file (single source of truth); fall back to an
# embedded copy so the script also works piped standalone (ssh 'bash -s'). The
# embedded copy is kept byte-identical to 10-size-cap.conf so both paths deploy
# exactly the same file (no cosmetic drift between repo and host).
if [[ -n "${SRC}" && -f "${SRC}" ]]; then
  desired="$(cat "${SRC}")"
else
  desired="$(cat <<'EOF'
# Fleet journald size cap — quality-gate fix-31.
#
# A single chatty service (mini's upsmon retrying a dead NUT server every ~5s)
# filled the persistent journal to 4.1G, because journald ships with NO size
# cap (the default SystemMaxUse is 10% of the filesystem — many GB on these
# hosts). Bound it so no runaway logger can silently eat the disk again.
#
# Deployed to /etc/systemd/journald.conf.d/10-size-cap.conf on mini + rig by
# configs/host/common/journald/apply-journald-cap.sh, then journald is restarted.
# The NAS runs DSM (its own log rotation) and is intentionally excluded.
#
# Verified by checks.d/power-journal.yaml (journal-not-bloated-{mini,rig}).
[Journal]
SystemMaxUse=1G
SystemMaxFileSize=128M
EOF
)"
fi

if [[ -f "${DEST}" ]] && [[ "$(cat "${DEST}")" == "${desired}" ]]; then
  log "${DEST} already current."
else
  log "Writing ${DEST}."
  printf '%s\n' "${desired}" >"${DEST}"
  chmod 0644 "${DEST}"
  log "Restarting systemd-journald to apply the cap."
  systemctl restart systemd-journald
fi

# Enforce immediately: vacuum anything already over the cap.
log "Vacuuming journal down to the 1G cap."
journalctl --vacuum-size=1G >/dev/null 2>&1 || true

log "Current usage: $(journalctl --disk-usage 2>/dev/null | sed 's/^[^0-9]*//')"
log "Done."
