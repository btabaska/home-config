#!/bin/sh
# DSM boot-up task (17.task) — fix-67 / SL30. Raise the per-user inotify watch
# limit so the Syncthing hub's filesystem watcher can arm on EVERY folder.
#
# DSM ships fs.inotify.max_user_watches at 8192, which the hub exhausts at its
# SECOND folder: `default` (Sync) consumes the budget and `game-saves` comes up
# with watchError "failed to set up inotify handler. Please increase inotify
# limits", so NAS-side changes to game-saves (a manual save restore) only
# propagate on the ~1h periodic rescan instead of instantly. DSM does not persist
# /etc/sysctl.conf across reboots, so re-apply at boot. Idempotent (sysctl -w just
# sets the value). Guarded live by check syncthing-hub-inotify-live.
WATCHES=204800
LOG=/var/log/syncthing-inotify-limit.log
sysctl -w fs.inotify.max_user_watches="$WATCHES" >/dev/null 2>&1
echo "$(date -Is) fs.inotify.max_user_watches=$(cat /proc/sys/fs/inotify/max_user_watches)" >> "$LOG"
