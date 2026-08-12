# NAS tasks scripts

`foss-setup/scripts/nas/` — 20 script(s).

| Script | Role |
|---|---|
| [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md) | Apply updated compose files (restart: always) on the NAS without recreating containers. |
| [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md) | run ON the nas (Synology DS920+) as root (DSM task id=14). |
| [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md) | run ON the nas (Synology DS920+). |
| [`harden-backups-acl.sh`](harden-backups-acl-sh.md) | run ON the nas (Synology DS920+) as root. fix-53 |
| [`immich-db-dump.sh`](immich-db-dump-sh.md) | Nightly Immich Postgres dump (DSM Task Scheduler, 02:30) + Healthchecks ping. |
| [`immich-pg-dump.sh`](immich-pg-dump-sh.md) | DEPRECATED — superseded by immich-db-dump.sh, which is the script DSM task 9 |
| [`import-roms-v3.sh`](import-roms-v3-sh.md) | copy the remaining PixelCove game sets from the seedbox |
| [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md) | copy the seedbox "manual" ROM collections into the |
| [`install-beets-task.sh`](install-beets-task-sh.md) | — |
| [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md) | — |
| [`install-kiwix-refresh-task.sh`](install-kiwix-refresh-task-sh.md) | run ON the nas as root. Installs DSM Task |
| [`install-mylar3-perms-guard-task.sh`](install-mylar3-perms-guard-task-sh.md) | run ON the nas as root. Installs DSM Task |
| [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md) | Install NAS docker health cron + fix Task Scheduler repeat-hour bug. |
| [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md) | run ON the nas as root. Installs DSM Task |
| [`install-syncthing-inotify-task.sh`](install-syncthing-inotify-task-sh.md) | run ON the nas as root. Installs DSM Task |
| [`move-games.sh`](move-games-sh.md) | RELOCATE the complete game payloads from the seedbox into the |
| [`mylar3-perms-guard.sh`](mylar3-perms-guard-sh.md) | run ON the nas (Synology DS920+) as root (DSM task id=16, |
| [`nas-docker-health.sh`](nas-docker-health-sh.md) | NAS Docker stack health check + auto-recovery. |
| [`recover-docker-stacks.sh`](recover-docker-stacks-sh.md) | Recover Synology Container Manager + NAS compose stacks after dockerd crash. |
| [`resume-games.sh`](resume-games-sh.md) | sequential resume (2026-08-11 21:45) of the two seedbox->NAS |

[← All scripts](../index.md)
