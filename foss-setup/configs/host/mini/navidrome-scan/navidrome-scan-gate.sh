#!/usr/bin/env bash
# navidrome-scan-gate.sh — mount-gated Navidrome scan trigger (fix-49).
#
# Why this exists: Navidrome's own periodic scanner (ND_SCANNER_SCHEDULE) is now
# DISABLED ("0"). On 2026-08-01 an hourly QUICK scan observed the read-only CIFS
# music root as momentarily EMPTY (soft-mount short read) and mass-flagged every
# track missing=1 — a 30h whole-library outage — and quick scans can NEVER clear
# a missing flag. This gate is the SOLE periodic scan driver and refuses to scan
# unless the CIFS root is actually populated, so a transient empty read can no
# longer reach the scanner. If it finds the library ALREADY mass-flagged missing
# while the mount is healthy, it triggers a FULL scan to self-heal (recovery that
# used to require a human). Runs from navidrome-scan.timer every 15 min.
#
# Auth: reads the Navidrome admin Subsonic token from /etc/navidrome-scan.env
# (NAVIDROME_USER / NAVIDROME_TOKEN / NAVIDROME_SALT, root:root 0600). The scan
# runs IN the Navidrome server process (single sqlite writer) — never a second
# `navidrome scan` process, which would contend with the live DB.
set -euo pipefail

MUSIC_MP="${MUSIC_MP:-/mnt/nas/music}"
MIN_ROOT_ENTRIES="${MIN_ROOT_ENTRIES:-10}"     # library has ~47 top-level artist dirs
ENV_FILE="${ENV_FILE:-/etc/navidrome-scan.env}"
BASE="http://localhost:4533/rest"; V=1.16.1; C=scan-gate

# shellcheck disable=SC1090
. "$ENV_FILE"

api() { # $1 = view (e.g. startScan), $2 = extra query (e.g. fullScan=true)
  curl -fsS --max-time 45 \
    "$BASE/$1.view?u=${NAVIDROME_USER}&t=${NAVIDROME_TOKEN}&s=${NAVIDROME_SALT}&v=${V}&c=${C}&f=json${2:+&$2}"
}

# Navidrome must be up (a manual full-scan recovery stops it briefly).
if [ "$(docker inspect -f '{{.State.Running}}' navidrome 2>/dev/null)" != "true" ]; then
  echo "SKIP navidrome-not-running"; exit 0
fi

# ── mount-gate ────────────────────────────────────────────────────────────────
# The CIFS root must actually be populated. A momentarily-empty read here is
# exactly what greyed out the whole library on 2026-08-01, so we simply do not
# scan when the root is empty/short (covers "NAS down", "share unmounted", and
# "soft-mount returned a short listing").
# grep -cv exits 1 when nothing matches (empty/absent root) — that is the case we
# most need to handle, so `|| true` keeps it from tripping set -e/pipefail and we
# fall through to a clean GATE_SKIP (exit 0, no OnFailure page; the stale scan is
# what the navidrome-scan-fresh dead-man pages on).
entries=$(ls -1 "$MUSIC_MP" 2>/dev/null | grep -cvxE '#recycle|@eaDir' || true)
entries=${entries:-0}
if [ "$entries" -lt "$MIN_ROOT_ENTRIES" ]; then
  echo "GATE_SKIP empty-or-short root_entries=${entries:-0} min=${MIN_ROOT_ENTRIES}"
  exit 0
fi

# Don't stack on an in-flight scan.
if api getScanStatus 2>/dev/null | grep -q '"scanning":true'; then
  echo "SKIP scan-in-progress"; exit 0
fi

# Quick scan normally; FULL scan to self-heal a mass-missing library (only ever
# reached once the mount-gate above has proven the root is healthy).
db=$(docker exec navidrome sqlite3 -readonly /data/navidrome.db \
  "select count(*)||' '||coalesce(sum(missing),0) from media_file;" 2>/dev/null) || db="0 0"
total=${db% *}; missing=${db#* }
if [ "${total:-0}" -gt 0 ] && [ "$(( ${missing:-0} * 2 ))" -ge "${total:-0}" ]; then
  api startScan "fullScan=true" >/dev/null
  echo "SCAN_TRIGGERED full self-heal missing=${missing}/${total} root_entries=${entries}"
else
  api startScan >/dev/null
  echo "SCAN_TRIGGERED quick missing=${missing}/${total} root_entries=${entries}"
fi
