# `harden-backups-acl.sh`

> run ON the nas (Synology DS920+) as root. fix-53

**Path:** `foss-setup/scripts/nas/harden-backups-acl.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 harden-backups-acl.sh — run ON the nas (Synology DS920+) as root. fix-53
 (fleet-sweep 2026-08-02, finding SM42): the /volume1/backups shared folder (where
 Home Assistant writes its daily client-side-ENCRYPTED offsite backup tars via the
 ha-backup SMB user) granted full rwxpdD (write + DELETE) to EVERY NAS group —
 administrators, ha-backup, media, users, http, household, docker-service — and those
 ACEs are inheritable (fd--), so every new tar inherited them. Any NAS account, a
 compromised web service (http), or a compromised container (docker-service) could
 silently delete or replace the only off-eMMC HA backup leg (integrity/availability
 risk; read is mitigated — tars are encrypted, key at vault hosts.ha.backup_password).

 This TIGHTENS the directory's inheritable ACL so only administrators (restore/admin)
 and ha-backup (the writer) keep write+delete; every other group is downgraded to
 READ-ONLY (kept, not removed — no reader breaks, tars stay encrypted). It then
 -enforce-inherit's the corrected template onto the existing tars. New HA backups
 inherit the tightened perms automatically — this IS the source fix (HA writes over
 SMB and files inherit the folder ACL). Idempotent: re-running only touches groups
 that still have write. Monitored by verification check nas-ha-backup-acl (crit).
```

## Environment / variables referenced

`ACL`, `DIR`, `EUID`, `NONWRITERS`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-mylar3-perms-guard-task.sh`](install-mylar3-perms-guard-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [`mylar3-perms-guard.sh`](mylar3-perms-guard-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
