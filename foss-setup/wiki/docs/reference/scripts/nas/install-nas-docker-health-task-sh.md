# `install-nas-docker-health-task.sh`

> Install NAS docker health cron + fix Task Scheduler repeat-hour bug.

**Path:** `foss-setup/scripts/nas/install-nas-docker-health-task.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 Install NAS docker health cron + fix Task Scheduler repeat-hour bug.
 Run once on the NAS as root:
   sudo bash /volume1/scripts/nas/install-nas-docker-health-task.sh
```

## Environment / variables referenced

`EUID`, `HEALTH_CMD_B64`, `TASK_DIR`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`harden-backups-acl.sh`](harden-backups-acl-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-kiwix-refresh-task.sh`](install-kiwix-refresh-task-sh.md)
- [`install-mylar3-perms-guard-task.sh`](install-mylar3-perms-guard-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
