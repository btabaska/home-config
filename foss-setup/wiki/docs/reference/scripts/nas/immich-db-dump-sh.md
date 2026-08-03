# `immich-db-dump.sh`

> Nightly Immich Postgres dump (DSM Task Scheduler, 02:30) + Healthchecks ping.

**Path:** `foss-setup/scripts/nas/immich-db-dump.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 Nightly Immich Postgres dump (DSM Task Scheduler, 02:30) + Healthchecks ping.
 DSM rewrites /etc/crontab, so this must ONLY be scheduled as a DSM task —
 never as a raw crontab line (that's how the 2026-07-07 schedule got lost).
```

## Environment / variables referenced

`DOCKER`, `KEEP_DAYS`, `OUT_DIR`, `PING_URL`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`harden-backups-acl.sh`](harden-backups-acl-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-mylar3-perms-guard-task.sh`](install-mylar3-perms-guard-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [`install-syncthing-inotify-task.sh`](install-syncthing-inotify-task-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
