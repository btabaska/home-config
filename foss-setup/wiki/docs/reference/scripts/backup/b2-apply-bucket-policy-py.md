# `b2-apply-bucket-policy.py`

> b2-apply-bucket-policy — idempotently (re)apply the B2 bucket policy (fix-22).

**Path:** `foss-setup/scripts/backup/b2-apply-bucket-policy.py` · **Category:** [Backup & restore](index.md) · **Type:** Python

## What it does

```text
b2-apply-bucket-policy — idempotently (re)apply the B2 bucket policy (fix-22).

The desired cloud state is code here so a rebuilt/replaced bucket can be
restored to policy instead of relying on memory of what the web console once
said. Verification of this state runs daily via
verification/bin/b2-bucket-guard.py; THIS script is the repair tool.

Policy (2026-07-17):
  bucket-restic       file lock ON, default retention GOVERNANCE 30d,
                      lifecycle daysFromHidingToDeleting=30. Existing upload
                      versions without retention get a 30d GOVERNANCE backfill
                      (--backfill).
  bucket-hyper-backup deliberately NO lock/retention — Hyper Backup Smart
                      Recycle rotation must delete old versions (accepted
                      M37); do not "fix" this without rethinking HB rotation.

Requires a key with writeBucketRetentions/writeFileRetentions — i.e. the B2
MASTER key, which was retired from the vault to offline storage 2026-07-17.
Pass it explicitly:
    B2_MASTER_KEY_ID=... B2_MASTER_KEY=... ./b2-apply-bucket-policy.py [--backfill]
The day-to-day vault ops key is read-only on purpose and will be rejected.
```

## See also

- [`ntfy-notify.sh`](ntfy-notify-sh.md)
- [`pre-backup-db-dumps.sh`](pre-backup-db-dumps-sh.md)
- [`restic-backup.sh`](restic-backup-sh.md)
- [`restic-latest-age.sh`](restic-latest-age-sh.md)
- [`restic-snapshot-hygiene.sh`](restic-snapshot-hygiene-sh.md)
- [`restore-test.sh`](restore-test-sh.md)
- [Backup & restore scripts](index.md) · [All scripts](../index.md)
