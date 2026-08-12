# `install-syncthing-inotify-task.sh`

> run ON the nas as root. Installs DSM Task

**Path:** `foss-setup/scripts/nas/install-syncthing-inotify-task.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 install-syncthing-inotify-task.sh — run ON the nas as root. Installs DSM Task
 Scheduler boot-up job 17 "syncthing inotify limit (fix-67/SL30)": at every boot,
 runs /volume1/docker/syncthing/boot-inotify-limit.sh which raises
 fs.inotify.max_user_watches to 204800 so the Syncthing hub can arm a filesystem
 watcher on every folder (DSM's 8192 default exhausts at the 2nd folder — see the
 boot script header).

 .task format cloned from 15.task (the shelfmark boot-rshared task). type=bootup
 jobs run from DSM's boot sequence, NOT crond — they do not appear in /etc/crontab;
 verify via `synoschedule --get 17` or the Task Scheduler UI. Never add raw cron
 lines (DSM rewrites /etc/crontab) — this .task-file path is the sanctioned method.
```

## Environment / variables referenced

`BOOT`, `CMD`, `CMD_B64`, `EUID`, `TASK`, `TASK_DIR`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`harden-backups-acl.sh`](harden-backups-acl-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`import-roms-v3.sh`](import-roms-v3-sh.md)
- [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-kiwix-refresh-task.sh`](install-kiwix-refresh-task-sh.md)
- [`install-mylar3-perms-guard-task.sh`](install-mylar3-perms-guard-task-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
