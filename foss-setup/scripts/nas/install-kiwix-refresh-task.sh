#!/usr/bin/env bash
# install-kiwix-refresh-task.sh — run ON the nas as root. Installs DSM Task
# Scheduler job 18 "kiwix library refresh (lai-12)": nightly at 05:15 runs
# /volume1/docker/kiwix/kiwix-library-refresh.sh, which rebuilds the Kiwix
# library.xml (kiwix-manage) + restarts kiwix-serve ONLY if the set of ZIM
# files in /volume1/zim changed (kiwix-serve cannot hot-add ZIMs).
#
# .task format cloned from install-mylar3-perms-guard-task.sh, minus the
# repeat window (single nightly run: repeat hour/min = 0). NEVER add raw
# lines to /etc/crontab on DSM — crond regenerates it from these .task files.
set -euo pipefail

TASK_DIR="/usr/syno/etc/synoschedule.d/root"
TASK="$TASK_DIR/18.task"
CMD="/bin/sh /volume1/docker/kiwix/kiwix-library-refresh.sh"
CMD_B64="L2Jpbi9zaCAvdm9sdW1lMS9kb2NrZXIva2l3aXgva2l3aXgtbGlicmFyeS1yZWZyZXNoLnNo"

log() { printf '[%s] %s\n' "$(date -Is)" "$*"; }

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then echo "Run as root: sudo bash $0" >&2; exit 1; fi

[ -f "$TASK" ] && { log "18.task already exists — skipping create"; exit 0; }

cat >"$TASK" <<EOF
id=18
last work hour=5
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
name=kiwix library refresh (lai-12)
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
run hour=5
edit form=SYNO.SDS.TaskScheduler.Script.FormPanel
app=SYNO.SDS.TaskScheduler.Script
run min=15
start month=0
can edit name=1
start year=0
can run from ui=1
repeat min=0
cmdArgv=
EOF
chmod 660 "$TASK"; chown root:administrators "$TASK"
log "Created 18.task: kiwix library refresh (nightly 05:15)"

/usr/syno/bin/synosystemctl restart crond 2>/dev/null \
  || log "WARNING: crond restart failed — run: sudo synosystemctl restart crond"
sleep 3
# crontab lines reference the task by id (synoschedtask --run id=18), not by script name
grep -qE -- "--run id=18" /etc/crontab && log "18.task present in /etc/crontab" \
  || log "WARNING: id=18 not found in /etc/crontab"
