#!/bin/sh
# DSM boot-up task (15.task): the seedbox rclone mount comes up with PRIVATE
# propagation, but the shelfmark container bind-mounts it :rslave to read completed
# MAM torrents — which needs shared/slave propagation. Wait for the mount, re-apply
# rshared, then (re)start shelfmark so its bind succeeds. Idempotent + additive:
# make-rshared only adds propagation; it never disturbs the *arr containers that
# already bind /seedbox as private. Guarded live by check shelfmark-mam-path-ready.
MP=/volume1/mounts/seedbox-files
LOG=/var/log/shelfmark-rshared.log
i=0
while [ "$i" -lt 60 ]; do
  grep -q " $MP " /proc/self/mountinfo 2>/dev/null && break
  i=$((i+1)); sleep 5
done
if grep -q " $MP " /proc/self/mountinfo 2>/dev/null; then
  mount --make-rshared "$MP"
  echo "$(date -Is) rshared applied prop=$(grep " $MP " /proc/self/mountinfo | grep -oE 'shared:[0-9]+' | head -1)" >> "$LOG"
  /usr/local/bin/docker restart shelfmark >> "$LOG" 2>&1
else
  echo "$(date -Is) ERROR: $MP not mounted after 300s wait" >> "$LOG"
fi
