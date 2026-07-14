# `apply-compose-restart-policy.sh`

> Apply updated compose files (restart: always) on the NAS without recreating containers.

**Path:** `foss-setup/scripts/nas/apply-compose-restart-policy.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 Apply updated compose files (restart: always) on the NAS without recreating containers.
 Run on NAS as root: sudo bash /volume1/scripts/nas/apply-compose-restart-policy.sh
```

## Environment / variables referenced

`COMPOSE`, `DOCKER`, `EUID`

## See also

- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`nas-docker-health.sh`](nas-docker-health-sh.md)
- [`recover-docker-stacks.sh`](recover-docker-stacks-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
