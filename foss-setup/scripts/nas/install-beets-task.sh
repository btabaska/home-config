#!/usr/bin/env bash
set -euo pipefail
TASK="/usr/syno/etc/synoschedule.d/root/10.task"
CMD="/usr/local/bin/docker exec beets beet import -q /music/YouTube"
CMD_B64=$(printf '%s' "$CMD" | base64 | tr -d '\n')
[ -f "$TASK" ] && { echo "10.task exists"; exit 1; }
cat > "$TASK" <<T
id=10
last work hour=3
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
name=beets YouTube import
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
run hour=3
edit form=SYNO.SDS.TaskScheduler.Script.FormPanel
app=SYNO.SDS.TaskScheduler.Script
run min=15
start month=0
can edit name=1
start year=0
can run from ui=1
repeat min=0
cmdArgv=
T
chmod 660 "$TASK"; chown root:administrators "$TASK"
/usr/syno/bin/synosystemctl restart crond
sleep 3
grep -c "synoschedtask --run id=10" /etc/crontab
