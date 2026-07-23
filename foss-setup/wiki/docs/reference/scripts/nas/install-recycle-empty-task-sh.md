# `install-recycle-empty-task.sh`

> run ON the nas as root. Installs DSM Task

**Path:** `foss-setup/scripts/nas/install-recycle-empty-task.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 install-recycle-empty-task.sh — run ON the nas as root. Installs DSM Task
 Scheduler job 14 "Empty recycle bins (30d retention)": monthly on the 1st at
 05:00 (inside the 4-7AM EST disruptive window), runs
 /volume1/scripts/nas/empty-recycle-30d.sh (quality-gate L50 hardening).

 .task format cloned from install-immich-dump-task.sh (daily) with the monthly
 fields taken from the DSM-native Auto S.M.A.R.T. Test task
 (3.backup/3.task_251208*: type=monthly, week=0000000, start day = day-of-month).
```

## Environment / variables referenced

`CMD`, `CMD_B64`, `TASK`, `TASK_DIR`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`nas-docker-health.sh`](nas-docker-health-sh.md)
- [`recover-docker-stacks.sh`](recover-docker-stacks-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
