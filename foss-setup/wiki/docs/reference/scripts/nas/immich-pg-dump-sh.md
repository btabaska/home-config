# `immich-pg-dump.sh`

> Nightly Immich Postgres dump for Hyper Backup (nas-08 follow-up).

**Path:** `foss-setup/scripts/nas/immich-pg-dump.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## Synopsis

```
Schedule in DSM Task Scheduler: root, daily ~02:30, run:
```

## What it does

```text
 Nightly Immich Postgres dump for Hyper Backup (nas-08 follow-up).
 Schedule in DSM Task Scheduler: root, daily ~02:30, run:
   /volume1/docker/immich/immich-pg-dump.sh
```

## Environment / variables referenced

`BACKUP_DIR`, `OUT`, `STAMP`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [`nas-docker-health.sh`](nas-docker-health-sh.md)
- [`recover-docker-stacks.sh`](recover-docker-stacks-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
