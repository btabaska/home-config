# `move-games.sh`

> RELOCATE the complete game payloads from the seedbox into the

**Path:** `foss-setup/scripts/nas/move-games.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 move-games.sh — RELOCATE the complete game payloads from the seedbox into the
 NAS RomM library (2026-08-11). Uses `rclone move`: each file is verified on
 the NAS before it is deleted from the seedbox.

 2026-08-11 22:00 REWRITE (operator correction): the PS3 torrent is 4.6T
 TOTAL but was only partially downloaded — 617G real data on seedbox disk.
 Sparse-block census (allocated >= size == complete, any hole = broken
 archive): 39/575 remaining archives complete (359 GiB); 536 were sparse
 hulls. The PS3 leg moves ONLY the complete archives, via --files-from
 ps3-complete.list. 2026-08-11 22:20 (operator decision): the hulls are NOT
 wanted — all 536 deleted from the seedbox, and the 10 broken first-run
 archives (all zero-holed on deep scan) deleted from the NAS quarantine.
 Only the 39 listed games survive; the other 546 would need a fresh
 re-download of the torrent if ever wanted.
 The NDS set censused fully complete (6573/6573 files) — moves whole.
 After both moves, a zero-run scan re-verifies every landed ps3 archive
 (any all-zero 1MiB chunk = a missed hole) and STATUS carries the count.
```

## Environment / variables referenced

`LOG`, `PS3HOLES`, `ROMS`, `RSRC`, `STATUS`

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
