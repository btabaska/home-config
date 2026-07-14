# `nas-docker-health.sh`

> NAS Docker stack health check + auto-recovery.

**Path:** `foss-setup/scripts/nas/nas-docker-health.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 NAS Docker stack health check + auto-recovery.
 Idempotent: safe to run every 15 min from DSM Task Scheduler (root).

 Brings up all compose stacks, verifies critical LAN ports, logs results.
 Optional ntfy alert when services stay down after recovery (see health.env).

 Install: sudo bash /volume1/scripts/nas/install-nas-docker-health-task.sh
```

## Environment / variables referenced

`CHECKS`, `COMPOSE`, `DOCKER`, `ENV_FILE`, `EUID`, `LOG`, `NTFY_TOKEN`, `NTFY_TOPIC`, `NTFY_URL`, `START_SCRIPT`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`recover-docker-stacks.sh`](recover-docker-stacks-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
