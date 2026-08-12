# `import-roms-v3.sh`

> copy the remaining PixelCove game sets from the seedbox

**Path:** `foss-setup/scripts/nas/import-roms-v3.sh` · **Category:** [NAS tasks](index.md) · **Type:** Bash

## What it does

```text
 import-roms-v3.sh — copy the remaining PixelCove game sets from the seedbox
 into the NAS RomM library, so they exist on the NAS BEFORE the seedbox
 torrents are removed (2026-08-11, operator request). COPY ONLY — seedbox
 payloads keep seeding untouched; removal happens only after verify.

 Deferred (NOT copied here): the two "Sony PlayStation 3 (USA)" sets and the
 "Redump - Sony - PlayStation (America)" set are in Deluge Error state
 (incomplete downloads) — importing partial data would produce broken games.
 Complete those first, then import.

 2026-08-11 21:45 (resume session): first run was SIGTERMed at 13:54:39 —
 collateral of the seedbox rclone-mount remount cycle (pkill rclone) — while
 mid-PS2_Part4. Re-run is safe (rclone copy skips transferred files). The
 "Bios collection Playstation 1" and "gog_games_s" legs are DISABLED below:
 both sources vanished from the seedbox between authoring and resume
 (presumably deleted in the same-day Deluge torrent cleanup) and never
 reached the NAS — re-source them if still wanted.
```

## Environment / variables referenced

`FAILS`, `GAMES`, `LOG`, `ROMS`, `RSRC`, `STATUS`

## See also

- [`apply-compose-restart-policy.sh`](apply-compose-restart-policy-sh.md)
- [`empty-recycle-30d.sh`](empty-recycle-30d-sh.md)
- [`ensure-navidrome-music-ignore.sh`](ensure-navidrome-music-ignore-sh.md)
- [`harden-backups-acl.sh`](harden-backups-acl-sh.md)
- [`immich-db-dump.sh`](immich-db-dump-sh.md)
- [`immich-pg-dump.sh`](immich-pg-dump-sh.md)
- [`import-seedbox-roms.sh`](import-seedbox-roms-sh.md)
- [`install-beets-task.sh`](install-beets-task-sh.md)
- [`install-immich-dump-task.sh`](install-immich-dump-task-sh.md)
- [`install-kiwix-refresh-task.sh`](install-kiwix-refresh-task-sh.md)
- [`install-mylar3-perms-guard-task.sh`](install-mylar3-perms-guard-task-sh.md)
- [`install-nas-docker-health-task.sh`](install-nas-docker-health-task-sh.md)
- [NAS tasks scripts](index.md) · [All scripts](../index.md)
