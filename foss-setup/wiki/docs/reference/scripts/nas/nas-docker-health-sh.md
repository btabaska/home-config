# `nas-docker-health.sh`

> NAS Docker stack health check + auto-recovery.

**Path:** `foss-setup/scripts/nas/nas-docker-health.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 NAS Docker stack health check + auto-recovery.
 Idempotent: safe to run every 15 min from DSM Task Scheduler (root).

 Brings up all compose stacks, verifies critical LAN ports, and — for a service
 that is down AT THE PORT but whose container is running (an "Up but dead" wedge
 that `compose up --no-recreate` can never fix) — restarts that one container.
 Alerts (ntfy) are BACKED OFF and DEDUPED: a no-op run never pages, a genuine
 down state pages once per incident and then at most every PAGE_BACKOFF, and a
 recovery pages exactly once. See health.env for the ntfy config.

 History: before fix-62/SM55 this script checked stash for HTTP 200, but stash
 added auth ~2026-07-22 and now serves a 302 login redirect — a HEALTHY state
 that the old check read as DOWN, so it paged homelab-alerts priority-5 every
 15 min for hours (a no-op storm: `compose up` cannot "fix" a healthy service,
 and there was no backoff). Fixed here: stash accepts 200,302; restart-not-up
 semantics; per-service backoff state in STATE_DIR.

 Install: sudo bash /volume1/scripts/nas/install-nas-docker-health-task.sh
```

## Environment / variables referenced

`CHECKS`, `CODESOF`, `COMPOSE`, `CONTAINER_OF`, `DOCKER`, `ENV_FILE`, `EUID`, `HOSTOF`, `IS_DOWN`, `LOG`, `NEW_RESTART`, `NTFY_TOKEN`, `NTFY_TOPIC`, `NTFY_URL`

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
