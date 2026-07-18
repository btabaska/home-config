# Backup & restore scripts

`foss-setup/scripts/backup/` — 7 script(s).

| Script | Role |
|---|---|
| [`b2-apply-bucket-policy.py`](b2-apply-bucket-policy-py.md) | b2-apply-bucket-policy — idempotently (re)apply the B2 bucket policy (fix-22). |
| [`ntfy-notify.sh`](ntfy-notify-sh.md) | ntfy-notify.sh <failed-unit> — push a failure alert to the ntfy `backups` topic. |
| [`pre-backup-db-dumps.sh`](pre-backup-db-dumps-sh.md) | consistent database dumps on mini, run by |
| [`restic-backup.sh`](restic-backup-sh.md) | Tier 1 off-site backup of a Linux host (Ubuntu / CachyOS) |
| [`restic-latest-age.sh`](restic-latest-age-sh.md) | restic-latest-age — report whether the automated restic backup succeeded within |
| [`restic-snapshot-hygiene.sh`](restic-snapshot-hygiene-sh.md) | restic-snapshot-hygiene — assert every snapshot in this host's restic repo |
| [`restore-test.sh`](restore-test-sh.md) | prove a backup is RESTORABLE, not just that it ran. |

[← All scripts](../index.md)
