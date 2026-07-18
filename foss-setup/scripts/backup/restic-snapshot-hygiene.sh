#!/usr/bin/env bash
# restic-snapshot-hygiene — assert every snapshot in this host's restic repo
# belongs to a real fleet hostname and carries no test/junk tags (fix-22 L57:
# 8-byte 'ao-verify' smoke-test snapshots with synthetic hostnames fell into
# their own forget group and would have been retained forever), and that the
# latest snapshot ships no dedup-hostile bloat (fix-34 M29: 12G of AMP's own
# compressed backup zips rode along in BACKUP_PATHS and inflated B2 by ~12G —
# the class is "an app's internal backup artifacts inside the restic set").
#
# Deployed to /usr/local/bin/restic-snapshot-hygiene (root 0755) on mini + rig;
# invoked via /etc/sudoers.d/verification-restic by the daily verification
# sweep. Unlike restic-latest-age this DOES a live B2 round-trip — but only a
# snapshot listing (~2-5s with the nightly-warmed /var/cache/restic), well
# inside the 60s check timeout; it is untiered so it runs once daily.
# Prints "HYGIENE-OK ..." (exit 0) or "JUNK ..."/"NO-SIGNAL" (exit 1).
set -uo pipefail
ENV_FILE="${ENV_FILE:-/etc/restic/env}"
# real backup hostnames across the fleet (rig tags have flip-flopped
# cachyos/CachyOS casing after the 07-16 rebuild, so allow both)
ALLOWED_HOSTS="${ALLOWED_HOSTS:-macmini cachyos CachyOS}"

set -a; source "$ENV_FILE"; set +a
export RESTIC_CACHE_DIR="${RESTIC_CACHE_DIR:-/var/cache/restic}"

# mini: 0.19.1 hand-installed in /usr/local/bin (apt's 0.12 hard-deleted locks);
# rig: pacman restic on PATH. Resolve rather than hardcode (rollback-casualty
# lesson: PATH-resolve, don't pin paths that differ per host).
RESTIC="$(command -v /usr/local/bin/restic || command -v restic)" || {
  echo "NO-SIGNAL restic binary not found"; exit 1; }

json=$("$RESTIC" --no-lock snapshots --json 2>/dev/null) || {
  echo "NO-SIGNAL restic snapshots failed"; exit 1; }

ALLOWED_HOSTS="$ALLOWED_HOSTS" python3 - "$json" <<'PY'
import json, os, sys
allowed = set(os.environ["ALLOWED_HOSTS"].split())
snaps = json.loads(sys.argv[1])
junk = []
for s in snaps:
    tags = s.get("tags") or []
    if s["hostname"] not in allowed:
        junk.append(f"{s['short_id']} host={s['hostname']}")
    elif any(t.startswith(("ao-", "test")) for t in tags):
        junk.append(f"{s['short_id']} tags={','.join(tags)}")
if junk:
    print(f"JUNK {len(junk)} snapshot(s) with synthetic host or test tags "
          f"(forget policy will retain them forever): {'; '.join(junk)} "
          "— fix: restic forget <id>")
    sys.exit(1)
print(f"HYGIENE-OK {len(snaps)} snapshots, hosts+tags clean")
PY
rc=$?
[ "$rc" -eq 0 ] || exit "$rc"

# --- dedup-hostile-bloat scan (fix-34 M29). Only meaningful where the backup
# set contains the AMP instances dir, so hosts without it skip for free.
latest=$(printf '%s' "$json" | python3 -c '
import json, sys
snaps = json.load(sys.stdin)
amp = [s for s in snaps if any("/.ampdata/instances" in p for p in s.get("paths", []))]
print(amp[-1]["short_id"] if amp else "")')
if [ -n "$latest" ]; then
  zips=$("$RESTIC" --no-lock ls "$latest" 2>/dev/null \
    | grep -cE '/\.ampdata/instances/[^/]+/Backups/.+\.zip$')
  if [ "${zips:-0}" -gt 0 ]; then
    echo "BLOAT latest snapshot $latest carries $zips AMP backup zip(s) —" \
         "excludes-rig.txt Backups exclusion missing or bypassed (fix-34 M29)"
    exit 1
  fi
  echo "BLOAT-OK latest AMP-bearing snapshot $latest ships no app-internal backup zips"
fi
