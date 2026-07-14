# `ntfy-notify.sh`

> ntfy-notify.sh <failed-unit> — push a failure alert to the ntfy `backups` topic.

**Path:** `foss-setup/scripts/backup/ntfy-notify.sh` · **Category:** [Backup & restore](index.md) · **Type:** Bash

## What it does

```text
 ntfy-notify.sh <failed-unit> — push a failure alert to the ntfy `backups` topic.
 Wired as OnFailure=ntfy-notify@%n.service on restic-backup.service (mini + rig).

 Credentials: sources (in order, later wins for NTFY_* if set in both)
   /etc/verification/env  (mini — already holds NTFY_URL + NTFY_TOKEN)
   /etc/restic/env        (rig  — NTFY_URL/NTFY_TOKEN copied in at deploy time)
 NTFY_URL may point at any topic (e.g. .../verification); the last path segment
 is replaced with the `backups` topic.
```

## Environment / variables referenced

`HOST`, `NTFY_TOKEN`, `NTFY_URL`, `TOPIC_URL`, `UNIT`

## See also

- [`pre-backup-db-dumps.sh`](pre-backup-db-dumps-sh.md)
- [`restic-backup.sh`](restic-backup-sh.md)
- [`restic-latest-age.sh`](restic-latest-age-sh.md)
- [`restore-test.sh`](restore-test-sh.md)
- [Backup & restore scripts](index.md) · [All scripts](../index.md)
