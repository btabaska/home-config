#!/usr/bin/env bash
# mylar3-perms-guard.sh — run ON the nas (Synology DS920+) as root (DSM task id=16,
# every 15 min). fix-53 (fleet-sweep 2026-08-02, findings SM2/SM3): the Jul 27 mylar3
# deploy reintroduced the fix-23 file-permission failure class on the NAS.
#
# ROOT CAUSE (why a one-off chmod is not enough): mylar3 (github.com/mylar3/mylar3)
# calls os.umask(0) WITHOUT restoring it in PostProcessor.py and filechecker.py
# (e.g. filechecker.py:1917/1946 "this is probably redundant, but it doesn't hurt to
# clear the umask here"), so after the first grab/tag the whole mylar process runs at
# umask 0 and every file/dir it then creates under /config/mylar/cache and
# /config/mylar/.ComicTagger lands 0666/0777 (world-writable). Some paths are also
# hard-chmod'd 0777 (cmtagmylar.py:55, webviewer.py:137). The container entrypoint
# umask (compose) fixes config.ini's CREATE path but is DEFEATED by these os.umask(0)
# leaks for the cache — so this guard periodically re-secures the tree.
#
# config.ini itself (23 credential-class keys) is written IN-PLACE by configparser, so
# once it is 0600 the app's rewrites preserve the mode; we still re-assert it here as
# defense-in-depth (a fresh recreate would create it 0600 via the entrypoint umask).
#
# Anti-drift: mirrored in foss-setup/scripts/nas/. Installed by
# install-mylar3-perms-guard-task.sh (writes 16.task — never edit /etc/crontab on DSM).
# Re-greens verification checks nas-secret-file-perms (crit) + nas-worldwritable-sweep.
set -euo pipefail

CFG_ROOT="/volume1/docker/mylar3/config/mylar"
CONFIG_INI="$CFG_ROOT/config.ini"
PUID=1026   # btabaska — mylar/Komga owner
PGID=100    # users

[ -d "$CFG_ROOT" ] || { echo "mylar3 config dir absent ($CFG_ROOT) — nothing to do"; exit 0; }

# 1) config.ini: owner-only (no group/world read — it holds credential-class keys).
if [ -f "$CONFIG_INI" ]; then
  chown "$PUID:$PGID" "$CONFIG_INI" 2>/dev/null || true
  chmod 600 "$CONFIG_INI" 2>/dev/null || true
fi

# 2) cache + ComicTagger: owner-only (mylar recreates these world-writable — see header).
for d in "$CFG_ROOT/cache" "$CFG_ROOT/.ComicTagger"; do
  [ -e "$d" ] || continue
  find "$d" -type d -exec chmod 700 {} + 2>/dev/null || true
  find "$d" -type f -exec chmod 600 {} + 2>/dev/null || true
done

# 3) belt: strip any world-writable bit left anywhere under the config tree
#    (satisfies nas-worldwritable-sweep; -perm -0002 == the check's own predicate).
find "/volume1/docker/mylar3/config" \( -name @eaDir -o -name '#recycle' \) -prune -o \
  ! -type l -perm -0002 -exec chmod o-w {} + 2>/dev/null || true

# report (for /var/log + DSM task history)
ww=$(find /volume1/docker/mylar3/config \( -name @eaDir -o -name '#recycle' \) -prune -o \
  ! -type l -perm -0002 -print 2>/dev/null | wc -l | tr -d ' ')
cmode=$(stat -c '%a' "$CONFIG_INI" 2>/dev/null || echo '-')
echo "$(date -Is) mylar3-perms-guard: config.ini=$cmode world_writable_remaining=$ww"
