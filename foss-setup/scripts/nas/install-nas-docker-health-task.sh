#!/usr/bin/env bash
# Install NAS docker health cron + fix Task Scheduler repeat-hour bug.
# Run once on the NAS as root:
#   sudo bash /volume1/scripts/nas/install-nas-docker-health-task.sh
set -euo pipefail

TASK_DIR="/usr/syno/etc/synoschedule.d/root"
HEALTH_CMD_B64="YmFzaCAvdm9sdW1lMS9zY3JpcHRzL25hcy9uYXMtZG9ja2VyLWhlYWx0aC5zaA=="

log() { printf '[%s] %s\n' "$(date -Is)" "$*"; }

fix_repeat_window() {
  # DSM repeats a task within [run hour .. last work hour]. Setting only
  # "repeat hour" leaves "last work hour=23", which pins the whole window to
  # hour 0 (task fires 00:00-00:45 only). Both fields must be set.
  local task="$1"
  [[ -f "$task" ]] || return 0
  local changed=0
  grep -q '^repeat hour=0$' "$task" && { sed -i 's/^repeat hour=0$/repeat hour=23/' "$task"; changed=1; }
  grep -q '^last work hour=23$' "$task" && { sed -i 's/^last work hour=23$/last work hour=23/' "$task"; changed=1; }
  [[ $changed -eq 1 ]] && log "Fixed repeat window (repeat hour + last work hour → 23): $task"
}

install_health_task() {
  local task="${TASK_DIR}/5.task"
  [[ -f "$task" ]] && { log "Task 5 already exists — skipping create"; return 0; }

  cat >"$task" <<EOF
id=5
last work hour=23
can edit owner=1
can delete from ui=1
edit dialog=SYNO.SDS.TaskScheduler.EditDialog
type=daily
action=#common:run#: bash /volume1/scripts/nas/nas-docker-health.sh
systemd slice=
monthly week=0
can edit from ui=1
week=1111111
app name=#common:command_line#
name=Docker health check
can run app same time=1
owner=0
repeat min store config=[1,5,10,15,20,30]
repeat hour store config=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]
simple edit form=1
repeat hour=23
listable=1
app args={"notify_enable":false,"notify_if_error":false,"notify_mail":"","script":"bash /volume1/scripts/nas/nas-docker-health.sh"}
state=enabled
can run task same time=0
start day=0
cmd=${HEALTH_CMD_B64}
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
  chmod 660 "$task"
  chown root:administrators "$task"
  log "Created task 5: Docker health check (every 15 min, 24h repeat window)"
}

main() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Run as root: sudo bash $0" >&2
    exit 1
  fi

  mkdir -p /volume1/scripts/nas /var/log
  touch /var/log/nas-docker-health.log
  chmod 644 /var/log/nas-docker-health.log

  fix_repeat_window "${TASK_DIR}/3.task"
  fix_repeat_window "${TASK_DIR}/4.task"
  fix_repeat_window "${TASK_DIR}/5.task"
  install_health_task

  # crond (not synocrond) regenerates /etc/crontab from the .task files
  /usr/syno/bin/synosystemctl restart crond 2>/dev/null \
    || log "WARNING: crond restart failed — /etc/crontab NOT regenerated; run: sudo synosystemctl restart crond"

  log "Done. Test now: bash /volume1/scripts/nas/nas-docker-health.sh"
  log "Logs: tail -f /var/log/nas-docker-health.log"
}

main "$@"
