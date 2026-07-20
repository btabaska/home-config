# `import-seedbox-roms.sh`

> copy the seedbox "manual" ROM collections into the

**Path:** `foss-setup/scripts/nas/import-seedbox-roms.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 import-seedbox-roms.sh — copy the seedbox "manual" ROM collections into the
 RoMM library. Ran 2026-07-19/20 (repo copy is the provenance record; deployed
 ad-hoc to nas:/volume1/games/.rom-import/import.sh, launched as root via
 setsid nohup). Re-runnable: rclone copy skips already-transferred files, so a
 partial/failed run resumes safely. Copied ~790G in ~6h; see
 wiki services/romm for the resulting library state.
 Original header follows.

 copy the seedbox "manual" ROM collections into the RoMM
 library (2026-07-19, operator request). COPY ONLY — the seedbox payloads keep
 seeding untouched. v2: direct `rclone copy` (parallel transfers) instead of
 rsync-through-the-FUSE-mount — small-file sets crawled at ~30KB/s through the
 mount's serialized per-file SFTP round-trips. Runs as root (rclone conf is
 root's); ownership normalized to 1026:100 at the end. Region-sorted sets are
 flattened one level so RoMM doesn't read region folders as multi-part games.
```

## Environment / variables referenced

`EXTRAS`, `FAILS`, `NES_SORTED`, `ROMS`, `RSRC`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [`install-recycle-empty-task.sh`](install-recycle-empty-task-sh.md)
- [`nas-docker-health.sh`](nas-docker-health-sh.md)
- [`recover-docker-stacks.sh`](recover-docker-stacks-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
