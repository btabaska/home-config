# `restic-latest-age.sh`

> print freshness of the newest restic snapshot for this

**Path:** `foss-setup/scripts/backup/restic-latest-age.sh` · **Category:** [Backup & restore](index.md) · **Type:** Bash

## What it does

```text
 restic-latest-age.sh — print freshness of the newest restic snapshot for this
 host. Deployed to /usr/local/bin/restic-latest-age (root, 0755).

 WHY IT EXISTS: the verification runner executes as btabaska, but the restic
 env file (/etc/restic/env) is root-only 0600. Rather than loosening the env
 file's permissions, a single sudoers rule (/etc/sudoers.d/verification-restic)
 lets btabaska run EXACTLY this root-owned script with no arguments:
   btabaska ALL=(root) NOPASSWD: /usr/local/bin/restic-latest-age
 The verification check is then just: sudo -n /usr/local/bin/restic-latest-age

 Output:  "FRESH age_hours=N latest=<timestamp>"  exit 0   (age < MAX_AGE_HOURS)
          "STALE age_hours=N latest=<timestamp>"  exit 1
          "NO-SNAPSHOTS"                          exit 1
 MAX_AGE_HOURS defaults to 26 (daily timer + slack); env-overridable, NOT an
 argv argument — sudoers pins the zero-argument invocation.
```

## Environment / variables referenced

`ENV_FILE`, `MAX_AGE_HOURS`

## See also

- [`ntfy-notify.sh`](ntfy-notify-sh.md)
- [`pre-backup-db-dumps.sh`](pre-backup-db-dumps-sh.md)
- [`restic-backup.sh`](restic-backup-sh.md)
- [`restore-test.sh`](restore-test-sh.md)
- [Backup & restore scripts](index.md) · [All scripts](../index.md)
