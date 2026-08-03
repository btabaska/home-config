# `immich-pg-dump.sh`

> DEPRECATED — superseded by immich-db-dump.sh, which is the script DSM task 9

**Path:** `foss-setup/scripts/nas/immich-pg-dump.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 DEPRECATED — superseded by immich-db-dump.sh, which is the script DSM task 9
 actually runs (see install-immich-dump-task.sh). Kept only for provenance.
 It lacks the small-dump guard, full docker path, and healthchecks ping; do not
 schedule it. Retention aligned to KEEP_DAYS=7 (fix-60/SL29) to avoid a
 misleading 14-vs-7 discrepancy in the repo.
```

## Environment / variables referenced

`BACKUP_DIR`, `OUT`, `STAMP`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`harden-backups-acl.sh`](harden-backups-acl-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-mylar3-perms-guard-task.sh`](install-mylar3-perms-guard-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [`mylar3-perms-guard.sh`](mylar3-perms-guard-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
