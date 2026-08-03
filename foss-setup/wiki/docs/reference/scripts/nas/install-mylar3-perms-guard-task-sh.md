# `install-mylar3-perms-guard-task.sh`

> run ON the nas as root. Installs DSM Task

**Path:** `foss-setup/scripts/nas/install-mylar3-perms-guard-task.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 install-mylar3-perms-guard-task.sh — run ON the nas as root. Installs DSM Task
 Scheduler job 16 "mylar3 perms guard (fix-53)": every 15 minutes across the full
 day, runs /volume1/scripts/nas/mylar3-perms-guard.sh which re-secures mylar3's
 config.ini + cache/.ComicTagger tree (mylar leaks os.umask(0) so the cache goes
 world-writable during grabs — see the guard script header).

 .task format cloned from install-nas-docker-health-task.sh (type=daily + 15-min
 repeat across a 24h window). DSM repeats a task within [run hour .. last work hour];
 both "last work hour=23" and "repeat hour=23" must be set or the window pins to
 hour 0. crond (not synocrond) regenerates /etc/crontab from the .task files.
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
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [`mylar3-perms-guard.sh`](mylar3-perms-guard-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
