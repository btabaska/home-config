# `empty-recycle-30d.sh`

> run ON the nas (Synology DS920+) as root (DSM task id=14).

**Path:** `foss-setup/scripts/nas/empty-recycle-30d.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 empty-recycle-30d.sh — run ON the nas (Synology DS920+) as root (DSM task id=14).

 quality-gate 2026-07-16 L50 hardening: DSM #recycle bins regrow (youtube's hit
 81G / 6k+ files before the 2026-07-19 cleanup). Monthly DSM Task Scheduler job
 deletes recycle-bin entries older than RETENTION_DAYS (default 30), then
 re-creates the Navidrome ignore markers (fix-28 / L15) — an emptying pass
 would otherwise wipe the in-recycle marker and recycled tracks could reappear
 in the Navidrome library on the next scan.

 Install with install-recycle-empty-task.sh (writes 14.task — never edit
 /etc/crontab directly on DSM; it gets rewritten from synoschedule.d).
```

## Environment / variables referenced

`DAYS`, `RETENTION_DAYS`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [`nas-docker-health.sh`](nas-docker-health-sh.md)
- [`recover-docker-stacks.sh`](recover-docker-stacks-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
