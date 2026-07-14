# `restic-latest-age.sh`

> restic-latest-age — report whether the automated restic backup succeeded within

**Path:** `foss-setup/scripts/backup/restic-latest-age.sh` · **Category:** [Backup & restore](index.md) · **Type:** Bash

## What it does

```text
 restic-latest-age — report whether the automated restic backup succeeded within
 MAX_AGE_HOURS. Prints "FRESH ..." (exit 0) or "STALE ..."/"NO-BACKUP-SIGNAL"
 (exit 1). Deployed to /usr/local/bin/restic-latest-age (root, 0755). Consumed by
 the restic-snapshot-fresh-{mini,rig} verification checks.

 DOES NOT do a live B2 `restic snapshots` round-trip: that takes ~100s for this
 repo (all network wait) and blew the verification sweep's 60s timeout, FALSE-
 failing a crit check while backups were actually fine (observability-audit
 2026-07-14). Instead it reads two fast, local, authoritative signals:
   1. systemd's record of restic-backup.service (Result/ExecMainStatus/exit time)
      — set the instant the backup unit finishes; and
   2. a persisted success-marker it maintains itself, so the signal survives a
      reboot (systemd's per-unit record resets on boot; the file does not).
 restic-backup.service ends with `restic check`, so a successful unit run means
 the snapshot really is in B2.
```

## Environment / variables referenced

`MARKER`, `MAX_AGE_HOURS`, `RESTIC_SUCCESS_MARKER`, `RESTIC_UNIT`, `UNIT`

## See also

- [`ntfy-notify.sh`](ntfy-notify-sh.md)
- [`pre-backup-db-dumps.sh`](pre-backup-db-dumps-sh.md)
- [`restic-backup.sh`](restic-backup-sh.md)
- [`restore-test.sh`](restore-test-sh.md)
- [Backup & restore scripts](index.md) · [All scripts](../index.md)
