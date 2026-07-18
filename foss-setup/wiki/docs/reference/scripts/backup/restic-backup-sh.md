# `restic-backup.sh`

> Tier 1 off-site backup of a Linux host (Ubuntu / CachyOS)

**Path:** `foss-setup/scripts/backup/restic-backup.sh` · **Category:** [Backup & restore](index.md) · **Type:** Bash

## Synopsis

```
sudo ENV_FILE=/etc/restic/env ./restic-backup.sh
```

## What it does

```text
 restic-backup.sh — Tier 1 off-site backup of a Linux host (Ubuntu / CachyOS)
                    to Backblaze B2 via restic.

 What it does (idempotent — safe to re-run, designed for cron/systemd timer):
   1. Loads B2 creds + repo settings from an env file (NOT hardcoded).
   2. Initializes the restic repo on first run (no-op if it already exists).
   3. Runs an optional PRE_BACKUP_SCRIPT hook (e.g. consistent DB dumps on mini).
   4. Backs up the configured paths with sensible excludes
      (+ per-host RESTIC_EXCLUDE_FILE, e.g. /etc/restic/excludes.txt).
   5. Applies a forget retention policy daily; --prune once a week
      (PRUNE_WEEKDAY, default Sunday) to keep B2 API churn low.
   6. Runs a lightweight integrity check.

 Docs:
   restic + B2:      https://www.backblaze.com/docs/cloud-storage-integrate-restic-with-backblaze-b2
   restic manual:    https://restic.readthedocs.io/en/stable/
   retention/forget: https://restic.readthedocs.io/en/stable/060_forget.html

 Setup (once per host):
   sudo install -d -m 0700 /etc/restic
   sudo cp restic-backup.env.example /etc/restic/env   # then edit, chmod 600
   Password: either RESTIC_PASSWORD directly in the env file (0600 root — how
   mini/rig are deployed) or RESTIC_PASSWORD_FILE pointing at /etc/restic/password.
   # >>> Save that password in your password manager AND print it. No password = no restore. <<<

 Run:  sudo ENV_FILE=/etc/restic/env ./restic-backup.sh
 Prod: restic-backup.timer → restic-backup.service (OnFailure → ntfy-notify@)
```

## Environment / variables referenced

`BACKUP_PATHS`, `DEFAULT_BACKUP_PATHS`, `ENV_FILE`, `EXCLUDE_FILE_ARGS`, `FORCE_PRUNE`, `FORGET_ARGS`, `HOSTNAME_TAG`, `KEEP_DAILY`, `KEEP_MONTHLY`, `KEEP_WEEKLY`, `KEEP_YEARLY`, `PRE_BACKUP_SCRIPT`, `PRUNE_WEEKDAY`, `RESTIC_EXCLUDE_FILE`

## See also

- [`b2-apply-bucket-policy.py`](b2-apply-bucket-policy-py.md)
- [`ntfy-notify.sh`](ntfy-notify-sh.md)
- [`pre-backup-db-dumps.sh`](pre-backup-db-dumps-sh.md)
- [`restic-latest-age.sh`](restic-latest-age-sh.md)
- [`restic-snapshot-hygiene.sh`](restic-snapshot-hygiene-sh.md)
- [`restore-test.sh`](restore-test-sh.md)
- [Backup & restore scripts](index.md) · [All scripts](../index.md)
