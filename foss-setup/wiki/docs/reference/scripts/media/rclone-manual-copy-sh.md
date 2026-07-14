# `rclone-manual-copy.sh`

> the ONE scheduled rclone transfer (manual lane only)

**Path:** `foss-setup/scripts/media/rclone-manual-copy.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## What it does

```text
 ==============================================================================
 rclone-manual-copy.sh — the ONE scheduled rclone transfer (manual lane only)
 ==============================================================================
 Phase 2. Runs ON THE NAS (DS920+) on a schedule (e.g. every 15 min).

 This is the SINGLE scheduled rclone transfer in the whole system. It exists
 ONLY for the non-*arr / manual downloads lane:

   Seedbox Deluge `manual` label  ->  /home/hd34/btabaska/files/manual
   this job copies it down to      ->  /volume1/manual

 !!! IT MUST NEVER TOUCH THE *ARR LABEL FOLDERS !!!
 *arr-managed media (tv/movies/music/books) arrives via the LIVE rclone mount +
 the *arr import step — NOT via a scheduled copy. This job is scoped strictly to
 the `manual/` subtree so the two lanes never overlap or double-import.

 COPY (not move/sync): copy KEEPS the file seeding on the seedbox and is
 re-run-safe (idempotent — only new/changed files transfer). --min-age 5m skips
 files still being written. --transfers 4 bounds concurrency.

 THROWAWAY VARIANT (non-seeding public grabs you don't care to seed): use
   rclone move ... --min-age 5m --transfers 4
 `move` deletes the source after a successful transfer (stops seeding, frees
 seedbox space). Only use `move` for files you deliberately do NOT want to seed.

 DSM SETUP: Control Panel -> Task Scheduler -> Create -> Scheduled Task ->
   User-defined script, User = root, repeat every 15 minutes,
   Command = /volume1/scripts/media/rclone-manual-copy.sh
 On a systemd host instead, use a .service + .timer pair.

 Docs: https://rclone.org/commands/rclone_copy/
 ==============================================================================
```

## Environment / variables referenced

`DST`, `LOG`, `RCLONE`, `RCLONE_CONF`, `SRC`

## See also

- [`flac-to-alac-inplace.sh`](flac-to-alac-inplace-sh.md)
- [`immich-go-import.sh`](immich-go-import-sh.md)
- [`install-ipod-tools-cachyos.sh`](install-ipod-tools-cachyos-sh.md)
- [`install-slskd-native.sh`](install-slskd-native-sh.md)
- [`nas-music-to-alac-mirror.sh`](nas-music-to-alac-mirror-sh.md)
- [`rclone-seedbox-mount.sh`](rclone-seedbox-mount-sh.md)
- [`rclone-seedbox-watchdog.sh`](rclone-seedbox-watchdog-sh.md)
- [`readarr-copy-to-cwa-ingest.sh`](readarr-copy-to-cwa-ingest-sh.md)
- [`seedbox-sync.sh`](seedbox-sync-sh.md)
- [`verify-tailscale-seedbox.sh`](verify-tailscale-seedbox-sh.md)
- [`window-maint-unpackerr-rclone.sh`](window-maint-unpackerr-rclone-sh.md)
- [Media pipeline scripts](index.md) · [All scripts](../index.md)
