# `pre-backup-db-dumps.sh`

> consistent database dumps on mini, run by

**Path:** `foss-setup/scripts/backup/pre-backup-db-dumps.sh` · **Category:** [Backup & restore](index.md) · **Type:** Bash

## What it does

```text
 pre-backup-db-dumps.sh — consistent database dumps on mini, run by
 restic-backup.sh (PRE_BACKUP_SCRIPT) immediately before the restic snapshot.

 WHY: file-copying a live Postgres/MariaDB data dir is not a safe backup — the
 raw DB dirs (paperless-ngx/pgdata, miniflux/db, healthchecks/db,
 forgejo/data/db) are EXCLUDED from restic (see excludes-mini.txt) and these
 dumps are backed up instead. Restore = create DB, `gunzip -c x.sql.gz | psql`
 (dump_mariadb is kept for future MariaDB stacks; wallabag, its only user, was
 retired 2026-10-22 — its live dump target vanishing aborted every nightly
 restic run 2026-10-23..11-01 until it was dropped here).

 Dumps land in /opt/stacks/backups/db/ with FIXED filenames — restic snapshots
 provide the history, so no timestamped clutter and no local rotation needed.

 Container names/creds come from each stack's compose.yaml (all on this host):
   paperless_db    postgres  -U paperless    db paperless
   miniflux_db     postgres  -U miniflux     db miniflux
   healthchecks_db postgres  -U healthchecks db healthchecks
   forgejo_db      postgres  -U forgejo      db forgejo   (repos are on-disk
                   under /opt/stacks/forgejo/data/forgejo and backed up as files)

 Any failed or empty dump exits non-zero, which ABORTS the restic backup.
```

## Environment / variables referenced

`DB_DUMP_DIR`, `MYSQL_PASSWORD`, `MYSQL_USER`, `OUT_DIR`

## See also

- [`b2-apply-bucket-policy.py`](b2-apply-bucket-policy-py.md)
- [`ntfy-notify.sh`](ntfy-notify-sh.md)
- [`restic-backup.sh`](restic-backup-sh.md)
- [`restic-latest-age.sh`](restic-latest-age-sh.md)
- [`restic-snapshot-hygiene.sh`](restic-snapshot-hygiene-sh.md)
- [`restore-test.sh`](restore-test-sh.md)
- [Backup & restore scripts](index.md) · [All scripts](../index.md)
