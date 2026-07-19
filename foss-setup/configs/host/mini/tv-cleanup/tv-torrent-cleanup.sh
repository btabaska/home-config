#!/usr/bin/env bash
# tv-torrent-cleanup.sh — prune stale tv-torrent leftovers (fix-39 / M62).
# Replaces the broken "0 0 * * * /home/btabaska/bin" cron (exec of a directory,
# failed silently every midnight since Feb 2024).
# NOTE: /mnt/share/torrents is a LOCAL directory on the root LV — the NAS mount
# it once was is gone from fstab; nothing has written here since Oct 2025, so
# there is no seedbox re-copy risk. 30d keeps headroom if writes ever resume.
set -euo pipefail
TARGET=/mnt/share/torrents/tv
MAX_AGE_DAYS=30
if [[ ! -d "$TARGET" ]]; then
  echo "SKIP: $TARGET does not exist (share retired?)"
else
  mapfile -t victims < <(find "$TARGET" -mindepth 1 -maxdepth 1 -mtime +"$MAX_AGE_DAYS")
  echo "tv-cleanup: ${#victims[@]} entries older than ${MAX_AGE_DAYS}d"
  for v in "${victims[@]}"; do
    echo "removing: ${v##*/}"
    rm -rf -- "$v"
  done
  echo "tv-cleanup: done; $(find "$TARGET" -mindepth 1 -maxdepth 1 | wc -l) entries remain"
fi
# dead-man ping: cleanup success is what we attest, so ping failure only warns
# (the healthchecks grace window will alert if pings stop for real).
if [[ -n "${HEALTHCHECKS_PING_URL:-}" ]]; then
  curl -fsS -m 10 --retry 3 -o /dev/null "$HEALTHCHECKS_PING_URL" || echo "WARN: healthchecks ping failed"
fi
