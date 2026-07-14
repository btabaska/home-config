# `restore-test.sh`

> prove a backup is RESTORABLE, not just that it ran.

**Path:** `foss-setup/scripts/backup/restore-test.sh` · **Category:** [Backup & restore](index.md) · **Type:** Bash

## What it does

```text
 restore-test.sh — prove a backup is RESTORABLE, not just that it ran.
                   "A backup you have never restored is not a backup." Run monthly.

 Supports two backends:
   restic    — restores the latest snapshot into a temp dir and verifies files exist.
   borgmatic — extracts the latest archive into a temp dir and verifies files exist.

 Nothing is overwritten in place: everything is restored into a fresh mktemp dir,
 checked, then cleaned up. Read-only with respect to your live system and the repos.

 Docs:
   restic restore:  https://restic.readthedocs.io/en/stable/050_restore.html
   borg extract:    https://borgbackup.readthedocs.io/en/stable/usage/extract.html
   borgmatic:       https://torsion.org/borgmatic/docs/how-to/extract-a-backup/

 Usage:
   ENV_FILE=/etc/restic/env ./restore-test.sh restic
   ./restore-test.sh borgmatic [/etc/borgmatic/config.yaml]
```

## Environment / variables referenced

`BACKEND`, `CONFIG`, `ENV_FILE`, `LATEST`, `MIN_FILES`, `RESTIC_PASSWORD`, `RESTIC_PASSWORD_FILE`, `RESTIC_REPOSITORY`, `RESTORE_DIR`

## See also

- [`ntfy-notify.sh`](ntfy-notify-sh.md)
- [`pre-backup-db-dumps.sh`](pre-backup-db-dumps-sh.md)
- [`restic-backup.sh`](restic-backup-sh.md)
- [`restic-latest-age.sh`](restic-latest-age-sh.md)
- [Backup & restore scripts](index.md) · [All scripts](../index.md)
