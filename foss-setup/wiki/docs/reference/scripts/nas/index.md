# NAS tasks scripts

`foss-setup/scripts/nas/` — 11 script(s).

| Script | Role |
|---|---|
| [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md) | Apply updated compose files (restart: always) on the NAS without recreating containers. |
| [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md) | run ON the nas (Synology DS920+) as root (DSM task id=14). |
| [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md) | run ON the nas (Synology DS920+). |
| [`immich-db-dump.sh`](immich-db-dump-sh.md) | Nightly Immich Postgres dump (DSM Task Scheduler, 02:30) + Healthchecks ping. |
| [`immich-pg-dump.sh`](immich-pg-dump-sh.md) | Nightly Immich Postgres dump for Hyper Backup (nas-08 follow-up). |
| [`install-beets-task.sh`](install-beets-task-sh.md) | — |
| [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md) | — |
| [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md) | Install NAS docker health cron + fix Task Scheduler repeat-hour bug. |
| [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md) | run ON the nas as root. Installs DSM Task |
| [`nas-docker-health.sh`](nas-docker-health-sh.md) | NAS Docker stack health check + auto-recovery. |
| [`recover-docker-stacks.sh`](recover-docker-stacks-sh.md) | Recover Synology Container Manager + NAS compose stacks after dockerd crash. |

[← All scripts](../index.md)
