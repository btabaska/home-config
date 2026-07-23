# `ensure-navidrome-music-ignore.sh`

> run ON the nas (Synology DS920+).

**Path:** `foss-setup/scripts/nas/ensure-navidrome-music-ignore.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 ensure-navidrome-music-ignore.sh — run ON the nas (Synology DS920+).

 fix-28: Navidrome (on mini) mounts the NAS music share read-only and its 0.62
 "new scanner" indexed Synology's #recycle bin — 2 user-deleted tracks showed up
 as live, searchable library rows. The 0.62 scanner does NOT honor
 ND_IGNOREDPATTERNS; the working guard is an empty `.ndignore` marker at the
 folder root, which lives on the NAS filesystem and is therefore NOT restored by
 the git repo / ansible on a music-share rebuild. This idempotent script
 re-creates it. Run after any /volume1/music restore/rebuild.

 Guarded by verification check `navidrome-recycle-rows` (alerts if rows reappear).
```

## Environment / variables referenced

`MARKER`, `MUSIC`, `MUSIC_ROOT`, `RECYCLE`, `ROOT_MARKER`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [`nas-docker-health.sh`](nas-docker-health-sh.md)
- [`recover-docker-stacks.sh`](recover-docker-stacks-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
