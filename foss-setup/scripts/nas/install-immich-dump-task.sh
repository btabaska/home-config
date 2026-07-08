#!/usr/bin/env bash
set -euo pipefail
TASK_DIR="/usr/syno/etc/synoschedule.d/root"
TASK="$TASK_DIR/9.task"
CMD="bash /volume1/scripts/nas/immich-db-dump.sh"
CMD_B64=$(printf '%s' "$CMD" | base64 | tr -d '\n')
[ -f "$TASK" ] && { echo "9.task exists, aborting"; exit 1; }
cat > "$TASK" <<T
id=9
last work hour=2
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
name=Immich DB dump
can run app same time=1
owner=0
simple edit form=1
repeat hour=0
listable=1
app args={"notify_enable":false,"notify_if_error":false,"notify_mail":"","script":"$CMD"}
state=enabled
can run task same time=0
start day=0
cmd=$CMD_B64
run hour=2
edit form=SYNO.SDS.TaskScheduler.Script.FormPanel
app=SYNO.SDS.TaskScheduler.Script
run min=30
start month=0
can edit name=1
start year=0
can run from ui=1
repeat min=0
cmdArgv=
T
chmod 660 "$TASK"; chown root:administrators "$TASK"
echo "created 9.task"
/usr/syno/bin/synosystemctl restart crond 2>/dev/null || /usr/syno/bin/synosystemctl restart synocrond 2>/dev/null || echo "restart failed, trying synoservice"
sleep 3
grep -E "id=9|id=4|id=5" /etc/crontab
