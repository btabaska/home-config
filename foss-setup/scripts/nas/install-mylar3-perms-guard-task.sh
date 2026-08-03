#!/usr/bin/env bash
# install-mylar3-perms-guard-task.sh — run ON the nas as root. Installs DSM Task
# Scheduler job 16 "mylar3 perms guard (fix-53)": every 15 minutes across the full
# day, runs /volume1/scripts/nas/mylar3-perms-guard.sh which re-secures mylar3's
# config.ini + cache/.ComicTagger tree (mylar leaks os.umask(0) so the cache goes
# world-writable during grabs — see the guard script header).
#
# .task format cloned from install-nas-docker-health-task.sh (type=daily + 15-min
# repeat across a 24h window). DSM repeats a task within [run hour .. last work hour];
# both "last work hour=23" and "repeat hour=23" must be set or the window pins to
# hour 0. crond (not synocrond) regenerates /etc/crontab from the .task files.
set -euo pipefail

TASK_DIR="/usr/syno/etc/synoschedule.d/root"
TASK="$TASK_DIR/16.task"
CMD="bash /volume1/scripts/nas/mylar3-perms-guard.sh"
CMD_B64="YmFzaCAvdm9sdW1lMS9zY3JpcHRzL25hcy9teWxhcjMtcGVybXMtZ3VhcmQuc2g="

log() { printf '[%s] %s\n' "$(date -Is)" "$*"; }

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then echo "Run as root: sudo bash $0" >&2; exit 1; fi

[ -f "$TASK" ] && { log "16.task already exists — skipping create"; exit 0; }

cat >"$TASK" <<EOF
id=16
last work hour=23
can edit owner=1
can delete from ui=1
edit dialog=SYNO.SDS.TaskScheduler.EditDialog
type=daily
action=#common:run#: $CMD
systemd slice=
monthly week=0
can edit from ui=1
week=1111111
app name=#common:command_line#
name=mylar3 perms guard (fix-53)
can run app same time=1
owner=0
repeat min store config=[1,5,10,15,20,30]
repeat hour store config=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]
simple edit form=1
repeat hour=23
listable=1
app args={"notify_enable":false,"notify_if_error":false,"notify_mail":"","script":"$CMD"}
state=enabled
can run task same time=0
start day=0
cmd=${CMD_B64}
run hour=0
edit form=SYNO.SDS.TaskScheduler.Script.FormPanel
app=SYNO.SDS.TaskScheduler.Script
run min=0
start month=0
can edit name=1
start year=0
can run from ui=1
repeat min=15
cmdArgv=
EOF
chmod 660 "$TASK"; chown root:administrators "$TASK"
log "Created 16.task: mylar3 perms guard (every 15 min, 24h window)"

/usr/syno/bin/synosystemctl restart crond 2>/dev/null \
  || log "WARNING: crond restart failed — run: sudo synosystemctl restart crond"
sleep 3
grep -qE "id=16|mylar3-perms-guard" /etc/crontab && log "16.task present in /etc/crontab" \
  || log "WARNING: id=16 not found in /etc/crontab"
