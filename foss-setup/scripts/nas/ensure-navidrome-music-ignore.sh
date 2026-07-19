#!/usr/bin/env bash
# ensure-navidrome-music-ignore.sh — run ON the nas (Synology DS920+).
#
# fix-28: Navidrome (on mini) mounts the NAS music share read-only and its 0.62
# "new scanner" indexed Synology's #recycle bin — 2 user-deleted tracks showed up
# as live, searchable library rows. The 0.62 scanner does NOT honor
# ND_IGNOREDPATTERNS; the working guard is an empty `.ndignore` marker at the
# folder root, which lives on the NAS filesystem and is therefore NOT restored by
# the git repo / ansible on a music-share rebuild. This idempotent script
# re-creates it. Run after any /volume1/music restore/rebuild.
#
# Guarded by verification check `navidrome-recycle-rows` (alerts if rows reappear).
set -euo pipefail

MUSIC="${MUSIC_ROOT:-/volume1/music}"
RECYCLE="$MUSIC/#recycle"
MARKER="$RECYCLE/.ndignore"
ROOT_MARKER="$MUSIC/.ndignore"

# 2026-07-19 (quality-gate L15/L50): the in-recycle marker is deleted by any
# recycle-bin emptying pass (including the monthly empty-recycle-30d.sh task),
# so also keep a share-root .ndignore with a '#recycle' pattern — it lives
# outside the bin and survives emptying.
if [ -f "$ROOT_MARKER" ]; then
  echo "ok: $ROOT_MARKER already present"
else
  printf '#recycle\n' > "$ROOT_MARKER"
  chown 1026:100 "$ROOT_MARKER" 2>/dev/null || true
  chmod 644 "$ROOT_MARKER"
  echo "created: $ROOT_MARKER"
fi

if [ ! -d "$RECYCLE" ]; then
  echo "note: $RECYCLE does not exist yet (Synology creates it on first delete). Nothing to do."
  exit 0
fi

if [ -f "$MARKER" ]; then
  echo "ok: $MARKER already present"
else
  : > "$MARKER"
  echo "created: $MARKER (Navidrome will skip $RECYCLE on its next full scan)"
fi
