# `install-kiwix-refresh-task.sh`

> run ON the nas as root. Installs DSM Task

**Path:** `foss-setup/scripts/nas/install-kiwix-refresh-task.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## Synopsis

```
repeat window (single nightly run: repeat hour/min = 0). NEVER add raw
```

## What it does

```text
 install-kiwix-refresh-task.sh — run ON the nas as root. Installs DSM Task
 Scheduler job 18 "kiwix library refresh (lai-12)": nightly at 05:15 runs
 /volume1/docker/kiwix/kiwix-library-refresh.sh, which rebuilds the Kiwix
 library.xml (kiwix-manage) + restarts kiwix-serve ONLY if the set of ZIM
 files in /volume1/zim changed (kiwix-serve cannot hot-add ZIMs).

 .task format cloned from install-mylar3-perms-guard-task.sh, minus the
 repeat window (single nightly run: repeat hour/min = 0). NEVER add raw
 lines to /etc/crontab on DSM — crond regenerates it from these .task files.
```

## Environment / variables referenced

`CMD`, `CMD_B64`, `EUID`, `TASK`, `TASK_DIR`

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
- [`install-mylar3-perms-guard-task.sh`](install-mylar3-perms-guard-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
