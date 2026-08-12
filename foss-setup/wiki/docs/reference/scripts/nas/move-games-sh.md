# `move-games.sh`

> RELOCATE the two big already-on-disk game sets from the

**Path:** `foss-setup/scripts/nas/move-games.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 move-games.sh — RELOCATE the two big already-on-disk game sets from the
 seedbox into the NAS RomM library (2026-08-11). Uses `rclone move`: each file
 is checksum-verified on the NAS before it is deleted from the seedbox, so
 seedbox space frees incrementally and nothing is lost. Their Deluge torrents
 were already removed (data kept) before this runs.

 2026-08-11 21:45 (resume session): first run was SIGTERMed at 13:54:39
 (collateral of the seedbox rclone-mount remount cycle) after ~44G of ps3.
 Re-run is safe: already-moved files are gone from source, rclone continues
 with the rest. Size labels corrected — the PS3 set is 4.6T on seedbox disk
 (the original 625G figure was wrong), so this leg runs ~1.5-2 days. NOTE:
 the PS3 torrents were in Deluge Error state (incomplete) before removal —
 archive integrity is not guaranteed; a `7z t` sweep after the move is the
 way to find broken ones.
```

## Environment / variables referenced

`LOG`, `ROMS`, `RSRC`, `STATUS`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`harden-backups-acl.sh`](harden-backups-acl-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`import-roms-v3.sh`](import-roms-v3-sh.md)
- [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-kiwix-refresh-task.sh`](install-kiwix-refresh-task-sh.md)
- [`install-mylar3-perms-guard-task.sh`](install-mylar3-perms-guard-task-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
