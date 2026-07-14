# Backup & restore scripts

`foss-setup/scripts/backup/` — 5 script(s).

| Script | Role |
|---|---|
| [`ntfy-notify.sh`](ntfy-notify-sh.md) | ntfy-notify.sh <failed-unit> — push a failure alert to the ntfy `backups` topic. |
| [`pre-backup-db-dumps.sh`](pre-backup-db-dumps-sh.md) | consistent database dumps on mini, run by |
| [`restic-backup.sh`](restic-backup-sh.md) | Tier 1 off-site backup of a Linux host (Ubuntu / CachyOS) |
| [`restic-latest-age.sh`](restic-latest-age-sh.md) | print freshness of the newest restic snapshot for this |
| [`restore-test.sh`](restore-test-sh.md) | prove a backup is RESTORABLE, not just that it ran. |

[← All scripts](../index.md)
