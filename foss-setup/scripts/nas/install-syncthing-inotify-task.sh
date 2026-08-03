#!/usr/bin/env bash
# install-syncthing-inotify-task.sh — run ON the nas as root. Installs DSM Task
# Scheduler boot-up job 17 "syncthing inotify limit (fix-67/SL30)": at every boot,
# runs /volume1/docker/syncthing/boot-inotify-limit.sh which raises
# fs.inotify.max_user_watches to 204800 so the Syncthing hub can arm a filesystem
# watcher on every folder (DSM's 8192 default exhausts at the 2nd folder — see the
# boot script header).
#
# .task format cloned from 15.task (the shelfmark boot-rshared task). type=bootup
# jobs run from DSM's boot sequence, NOT crond — they do not appear in /etc/crontab;
# verify via `synoschedule --get 17` or the Task Scheduler UI. Never add raw cron
# lines (DSM rewrites /etc/crontab) — this .task-file path is the sanctioned method.
set -euo pipefail

TASK_DIR="/usr/syno/etc/synoschedule.d/root"
TASK="$TASK_DIR/17.task"
BOOT="/volume1/docker/syncthing/boot-inotify-limit.sh"
CMD="/bin/sh $BOOT"
CMD_B64="L2Jpbi9zaCAvdm9sdW1lMS9kb2NrZXIvc3luY3RoaW5nL2Jvb3QtaW5vdGlmeS1saW1pdC5zaA=="

log() { printf '[%s] %s\n' "$(date -Is)" "$*"; }

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then echo "Run as root: sudo bash $0" >&2; exit 1; fi
[ -f "$BOOT" ] || { echo "missing $BOOT — deploy it first" >&2; exit 1; }
chmod 755 "$BOOT"

[ -f "$TASK" ] && { log "17.task already exists — skipping create"; exit 0; }

cat >"$TASK" <<EOF
id=17
last work hour=0
can edit owner=1
can delete from ui=1
edit dialog=SYNO.SDS.TaskScheduler.EditDialog
type=bootup
action=#common:run#: $CMD
systemd slice=
monthly week=0
can edit from ui=1
week=1111111
app name=#common:command_line#
name=syncthing inotify limit (fix-67/SL30)
can run app same time=1
owner=0
simple edit form=1
repeat hour=0
listable=1
app args={"notify_enable":false,"notify_if_error":true,"notify_mail":"","script":"$CMD"}
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
repeat min=0
cmdArgv=
EOF
chmod 660 "$TASK"; chown root:administrators "$TASK"
log "Created 17.task: syncthing inotify limit (boot-up)"

/usr/syno/bin/synoschedule --reload 2>/dev/null \
  || log "note: synoschedule --reload unavailable; task applies on next boot regardless"
