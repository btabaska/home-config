# `resume-games.sh`

> sequential resume (2026-08-11 21:45) of the two seedbox->NAS

**Path:** `foss-setup/scripts/nas/resume-games.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 resume-games.sh — sequential resume (2026-08-11 21:45) of the two seedbox->NAS
 game transfers that were SIGTERMed at 13:54:39 (collateral of the seedbox
 rclone-mount remount cycle). Runs them ONE AT A TIME — two concurrent rclone
 transfer jobs on /volume1 is a known deadlock hazard, and running both at
 once is what the killed first attempt did. Both child scripts are idempotent
 (rclone copy/move skip already-transferred files) and own their STATUS files.
 Launched as root via: setsid nohup bash resume-games.sh
```

## Environment / variables referenced

`DIR`, `LOG`, `NTFY_TOKEN`, `NTFY_TOPIC`, `NTFY_URL`

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
