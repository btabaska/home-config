#!/usr/bin/env bash
# install-recycle-empty-task.sh — run ON the nas as root. Installs DSM Task
# Scheduler job 14 "Empty recycle bins (30d retention)": monthly on the 1st at
# 05:00 (inside the 4-7AM EST disruptive window), runs
# /volume1/scripts/nas/empty-recycle-30d.sh (quality-gate L50 hardening).
#
# .task format cloned from install-immich-dump-task.sh (daily) with the monthly
# fields taken from the DSM-native Auto S.M.A.R.T. Test task
# (3.backup/3.task_251208*: type=monthly, week=0000000, start day = day-of-month).
set -euo pipefail
TASK_DIR="/usr/syno/etc/synoschedule.d/root"
TASK="$TASK_DIR/14.task"
CMD="bash /volume1/scripts/nas/empty-recycle-30d.sh"
CMD_B64=$(printf '%s' "$CMD" | base64 | tr -d '\n')
[ -f "$TASK" ] && { echo "14.task exists, aborting"; exit 1; }
cat > "$TASK" <<T
id=14
last work hour=5
can edit owner=1
can delete from ui=1
edit dialog=SYNO.SDS.TaskScheduler.EditDialog
type=monthly
action=#common:run#: $CMD
systemd slice=
monthly week=0
can edit from ui=1
week=0000000
app name=#common:command_line#
name=Empty recycle bins (30d retention)
can run app same time=1
owner=0
simple edit form=1
repeat hour=0
listable=1
app args={"notify_enable":false,"notify_if_error":false,"notify_mail":"","script":"$CMD"}
state=enabled
can run task same time=0
start day=1
cmd=$CMD_B64
run hour=5
edit form=SYNO.SDS.TaskScheduler.Script.FormPanel
app=SYNO.SDS.TaskScheduler.Script
run min=0
start month=8
can edit name=1
start year=2026
can run from ui=1
repeat min=0
cmdArgv=
T
chmod 660 "$TASK"; chown root:administrators "$TASK"
echo "created 14.task"
/usr/syno/bin/synosystemctl restart crond 2>/dev/null || /usr/syno/bin/synosystemctl restart synocrond 2>/dev/null || echo "restart failed"
sleep 3
grep -E "id=14" /etc/crontab || { echo "WARNING: id=14 not in /etc/crontab"; exit 1; }
