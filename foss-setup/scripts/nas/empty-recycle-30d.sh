#!/usr/bin/env bash
# empty-recycle-30d.sh — run ON the nas (Synology DS920+) as root (DSM task id=14).
#
# quality-gate 2026-07-16 L50 hardening: DSM #recycle bins regrow (youtube's hit
# 81G / 6k+ files before the 2026-07-19 cleanup). Monthly DSM Task Scheduler job
# deletes recycle-bin entries older than RETENTION_DAYS (default 30), then
# re-creates the Navidrome ignore markers (fix-28 / L15) — an emptying pass
# would otherwise wipe the in-recycle marker and recycled tracks could reappear
# in the Navidrome library on the next scan.
#
# Install with install-recycle-empty-task.sh (writes 14.task — never edit
# /etc/crontab directly on DSM; it gets rewritten from synoschedule.d).
set -euo pipefail

DAYS="${RETENTION_DAYS:-30}"

for share in music youtube; do
  bin="/volume1/$share/#recycle"
  [ -d "$bin" ] || continue
  # -delete implies -depth: old files go first, then any dirs left empty.
  # Dirs still holding newer files fail the rmdir and are kept (stderr muted).
  find "$bin" -mindepth 1 -mtime "+$DAYS" ! -name '.ndignore' -delete 2>/dev/null || true
  echo "$share/#recycle: $(find "$bin" -mindepth 1 | wc -l) entries remain (kept < $DAYS days old)"
done

# Navidrome guards (L15 + fix-28 + fix-49):
# 1) share-root .ndignore with a '\#recycle' pattern (survives emptying passes).
#    fix-49 (2026-08-02): the pattern is `\#recycle`, NOT `#recycle`. `.ndignore`
#    is gitignore syntax where a leading `#` is a COMMENT, so a bare `#recycle`
#    left ZERO active patterns == an EMPTY .ndignore, which Navidrome reads as
#    "skip this whole folder" — at the music ROOT that greyed out all 3495 tracks
#    (missing=1). Rewrite when absent OR wrong (the old bare-`#recycle` file must
#    be corrected, not left in place). Do NOT revert to a bare '#recycle'.
if ! grep -qxF '\#recycle' /volume1/music/.ndignore 2>/dev/null; then
  printf '\\#recycle\n' > /volume1/music/.ndignore
  chown 1026:100 /volume1/music/.ndignore && chmod 644 /volume1/music/.ndignore
  echo "wrote /volume1/music/.ndignore (\\#recycle — escaped literal, not a comment)"
fi
# 2) empty marker inside #recycle (belt-and-braces for the 0.62 scanner)
if [ -d "/volume1/music/#recycle" ]; then
  : > "/volume1/music/#recycle/.ndignore"
fi
