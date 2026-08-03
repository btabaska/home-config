#!/usr/bin/env bash
# harden-backups-acl.sh — run ON the nas (Synology DS920+) as root. fix-53
# (fleet-sweep 2026-08-02, finding SM42): the /volume1/backups shared folder (where
# Home Assistant writes its daily client-side-ENCRYPTED offsite backup tars via the
# ha-backup SMB user) granted full rwxpdD (write + DELETE) to EVERY NAS group —
# administrators, ha-backup, media, users, http, household, docker-service — and those
# ACEs are inheritable (fd--), so every new tar inherited them. Any NAS account, a
# compromised web service (http), or a compromised container (docker-service) could
# silently delete or replace the only off-eMMC HA backup leg (integrity/availability
# risk; read is mitigated — tars are encrypted, key at vault hosts.ha.backup_password).
#
# This TIGHTENS the directory's inheritable ACL so only administrators (restore/admin)
# and ha-backup (the writer) keep write+delete; every other group is downgraded to
# READ-ONLY (kept, not removed — no reader breaks, tars stay encrypted). It then
# -enforce-inherit's the corrected template onto the existing tars. New HA backups
# inherit the tightened perms automatically — this IS the source fix (HA writes over
# SMB and files inherit the folder ACL). Idempotent: re-running only touches groups
# that still have write. Monitored by verification check nas-ha-backup-acl (crit).
set -euo pipefail

DIR="/volume1/backups"
ACL="/usr/syno/bin/synoacltool"
RO="r-x---a-R-c--"                      # read + traverse + read-attrs/ext-attrs/acl; NO w,p,d,D,A,W
# groups that must NOT be able to write/delete backups (downgrade to read-only):
NONWRITERS="media users http household docker-service"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then echo "Run as root: sudo bash $0" >&2; exit 1; fi
[ -d "$DIR" ] || { echo "$DIR absent — nothing to do"; exit 0; }

for grp in $NONWRITERS; do
  # -replace re-sorts the ACL, so re-read the current index each pass until the group
  # no longer has a full (write-bearing) ACE.
  while idx=$("$ACL" -get "$DIR" | grep "group:$grp:allow:rwxpdDaARWc" | grep -oE '\[[0-9]+\]' | tr -d '[]' | head -1); [ -n "${idx:-}" ]; do
    "$ACL" -replace "$DIR" "$idx" "group:$grp:allow:$RO:fd--" >/dev/null
    echo "downgraded group:$grp to read-only (was idx $idx)"
  done
done

# push the corrected inheritable ACL down onto the existing tars.
"$ACL" -enforce-inherit "$DIR" >/dev/null 2>&1 && echo "enforced inheritance onto existing children" \
  || echo "WARNING: enforce-inherit failed"

# verify: no non-writer group retains write on any tar
bad=0
for f in "$DIR"/*.tar; do
  [ -e "$f" ] || continue
  n=$("$ACL" -get "$f" 2>/dev/null | grep -Ec "group:(media|users|http|household|docker-service):allow:rwxpdD" || true)
  [ "$n" -eq 0 ] || { echo "STILL OPEN: $f ($n non-writer write ACEs)"; bad=1; }
done
[ "$bad" -eq 0 ] && echo "OK: no non-writer group has write/delete on any /volume1/backups tar"
exit "$bad"
