# `restic-snapshot-hygiene.sh`

> restic-snapshot-hygiene — assert every snapshot in this host's restic repo

**Path:** `foss-setup/scripts/backup/restic-snapshot-hygiene.sh` · **Category:** [Backup & restore](index.md) · **Type:** Bash

## What it does

```text
 restic-snapshot-hygiene — assert every snapshot in this host's restic repo
 belongs to a real fleet hostname and carries no test/junk tags (fix-22 L57:
 8-byte 'ao-verify' smoke-test snapshots with synthetic hostnames fell into
 their own forget group and would have been retained forever), and that the
 latest snapshot ships no dedup-hostile bloat (fix-34 M29: 12G of AMP's own
 compressed backup zips rode along in BACKUP_PATHS and inflated B2 by ~12G —
 the class is "an app's internal backup artifacts inside the restic set").

 Deployed to /usr/local/bin/restic-snapshot-hygiene (root 0755) on mini + rig;
 invoked via /etc/sudoers.d/verification-restic by the daily verification
 sweep. Unlike restic-latest-age this DOES a live B2 round-trip — but only a
 snapshot listing (~2-5s with the nightly-warmed /var/cache/restic), well
 inside the 60s check timeout; it is untiered so it runs once daily.
 Prints "HYGIENE-OK ..." (exit 0) or "JUNK ..."/"NO-SIGNAL" (exit 1).
```

## Environment / variables referenced

`ALLOWED_HOSTS`, `ENV_FILE`, `RESTIC`, `RESTIC_CACHE_DIR`

## See also

- [`b2-apply-bucket-policy.py`](b2-apply-bucket-policy-py.md)
- [`ntfy-notify.sh`](ntfy-notify-sh.md)
- [`pre-backup-db-dumps.sh`](pre-backup-db-dumps-sh.md)
- [`restic-backup.sh`](restic-backup-sh.md)
- [`restic-latest-age.sh`](restic-latest-age-sh.md)
- [`restore-test.sh`](restore-test-sh.md)
- [Backup & restore scripts](index.md) · [All scripts](../index.md)
