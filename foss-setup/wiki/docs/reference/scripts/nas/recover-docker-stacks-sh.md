# `recover-docker-stacks.sh`

> Recover Synology Container Manager + NAS compose stacks after dockerd crash.

**Path:** `foss-setup/scripts/nas/recover-docker-stacks.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 Recover Synology Container Manager + NAS compose stacks after dockerd crash.
 Thin wrapper — delegates to nas-docker-health.sh (full stack + port checks).
```

## Environment / variables referenced

`SCRIPT_DIR`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [`nas-docker-health.sh`](nas-docker-health-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
