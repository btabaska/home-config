#!/bin/sh
# kiwix-library-refresh.sh — lai-12: rebuild the Kiwix library.xml from /volume1/zim
# and bounce kiwix-serve, ONLY when the set of ZIM files actually changed.
# Live copy: /volume1/docker/kiwix/kiwix-library-refresh.sh (repo: foss-setup/configs/nas/kiwix/).
#
# Runs as ROOT (docker needs it on the NAS): DSM Task Scheduler job 18
# "kiwix library refresh (lai-12)" nightly at 05:15 (installer:
# foss-setup/scripts/nas/install-kiwix-refresh-task.sh), or by hand:
#   printf '%s\n' "$PW" | ssh nas 'sudo -S sh /volume1/docker/kiwix/kiwix-library-refresh.sh'
#
# Why this exists: kiwix-serve cannot hot-ADD ZIM files. New books need a
# library.xml rebuild (kiwix-manage, from the kiwix-tools sibling image — the
# serve image has no kiwix-manage) + a reload. --monitorLibrary on the serve
# side picks the rewritten XML up live; the container restart below is the
# deterministic fallback. The download queue mv's only COMPLETE files into
# /volume1/zim, so everything this script sees is safe to index.
# No-op fast path: identical file set + existing library.xml -> exit 0 silently
# (the nightly task costs nothing while the big downloads trickle in).
set -u

DOCKER=/usr/local/bin/docker
TOOLS_IMG='ghcr.io/kiwix/kiwix-tools:3.8.2@sha256:40ab5f450231836321d6a1e417006033db5883f883d08e85b246d2ecf8840a75'   # keep on the same release train as the serve image in docker-compose.yml
ZIM=/volume1/zim
LIB=/volume1/docker/kiwix/library
LOG=/volume1/docker/kiwix/logs/library-refresh.log
STATE=$LIB/.zims.state

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >> "$LOG"; }

cur=$(cd "$ZIM" 2>/dev/null && ls -1 *.zim 2>/dev/null | sort)
prev=$(cat "$STATE" 2>/dev/null || true)

if [ -z "$cur" ]; then
    log "no ZIM files in $ZIM yet — nothing to do"
    exit 0
fi
if [ "$cur" = "$prev" ] && [ -s "$LIB/library.xml" ]; then
    exit 0   # unchanged — the common nightly case
fi

n=$(printf '%s\n' "$cur" | grep -c .)
log "rebuilding library.xml ($n zims)"
rm -f "$LIB/library.new.xml"

# One kiwix-tools container run indexes everything (uid 1026 keeps files btabaska-owned).
if ! $DOCKER run --rm -u 1026:100 \
        -v "$ZIM":/data:ro -v "$LIB":/library \
        "$TOOLS_IMG" \
        /bin/sh -c 'for f in /data/*.zim; do kiwix-manage /library/library.new.xml add "$f" || exit 1; done' >> "$LOG" 2>&1; then
    log "FAIL: kiwix-manage rebuild errored — keeping previous library.xml"
    rm -f "$LIB/library.new.xml"
    exit 1
fi

mv "$LIB/library.new.xml" "$LIB/library.xml"
chown btabaska:users "$LIB/library.xml" 2>/dev/null || true
printf '%s\n' "$cur" > "$STATE"
chown btabaska:users "$STATE" 2>/dev/null || true

if $DOCKER ps --format '{{.Names}}' | grep -qx kiwix; then
    $DOCKER restart kiwix >/dev/null 2>&1 && log "library.xml refreshed ($n books) + kiwix restarted" \
        || log "WARNING: library.xml refreshed but kiwix restart failed"
else
    log "library.xml refreshed ($n books); kiwix container not running (compose up pending?)"
fi
