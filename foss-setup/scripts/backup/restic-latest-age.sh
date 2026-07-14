#!/usr/bin/env bash
# restic-latest-age — report whether the automated restic backup succeeded within
# MAX_AGE_HOURS. Prints "FRESH ..." (exit 0) or "STALE ..."/"NO-BACKUP-SIGNAL"
# (exit 1). Deployed to /usr/local/bin/restic-latest-age (root, 0755). Consumed by
# the restic-snapshot-fresh-{mini,rig} verification checks.
#
# DOES NOT do a live B2 `restic snapshots` round-trip: that takes ~100s for this
# repo (all network wait) and blew the verification sweep's 60s timeout, FALSE-
# failing a crit check while backups were actually fine (observability-audit
# 2026-07-14). Instead it reads two fast, local, authoritative signals:
#   1. systemd's record of restic-backup.service (Result/ExecMainStatus/exit time)
#      — set the instant the backup unit finishes; and
#   2. a persisted success-marker it maintains itself, so the signal survives a
#      reboot (systemd's per-unit record resets on boot; the file does not).
# restic-backup.service ends with `restic check`, so a successful unit run means
# the snapshot really is in B2.
set -uo pipefail
MAX_AGE_HOURS="${MAX_AGE_HOURS:-26}"
UNIT="${RESTIC_UNIT:-restic-backup.service}"
MARKER="${RESTIC_SUCCESS_MARKER:-/var/lib/restic-mon/last-success}"

emit() {  # $1=state $2=age_hours $3=source
  echo "$1 age_hours=$2 ($3)"
  [ "$1" = FRESH ] && exit 0 || exit 1
}

now=$(date +%s)

# 1) systemd record (authoritative + fast when the unit has run this boot)
ts=$(systemctl show "$UNIT" -p ExecMainExitTimestamp --value 2>/dev/null || true)
result=$(systemctl show "$UNIT" -p Result --value 2>/dev/null || true)
status=$(systemctl show "$UNIT" -p ExecMainStatus --value 2>/dev/null || true)
if [ -n "$ts" ] && [ "$result" = "success" ] && [ "$status" = "0" ]; then
  epoch=$(date -d "$ts" +%s 2>/dev/null || echo 0)
  if [ "$epoch" -gt 0 ]; then
    # keep the persistent marker in step so it survives the next reboot
    mkdir -p "$(dirname "$MARKER")" 2>/dev/null && touch -d "@$epoch" "$MARKER" 2>/dev/null || true
    age_h=$(( (now - epoch) / 3600 ))
    [ "$age_h" -lt "$MAX_AGE_HOURS" ] && emit FRESH "$age_h" "systemd" || emit STALE "$age_h" "systemd"
  fi
fi

# 2) systemd record absent this boot (e.g. just rebooted before the first run) —
#    fall back to the persisted marker from a prior successful run.
if [ -f "$MARKER" ]; then
  age_h=$(( (now - $(stat -c %Y "$MARKER")) / 3600 ))
  [ "$age_h" -lt "$MAX_AGE_HOURS" ] && emit FRESH "$age_h" "marker" || emit STALE "$age_h" "marker"
fi

echo "NO-BACKUP-SIGNAL (no ${UNIT} success record and no ${MARKER})"
exit 1
