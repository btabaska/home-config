# `immich-go-import.sh`

> import a mirrorless-camera SD card into Immich via immich-go.

**Path:** `foss-setup/scripts/media/immich-go-import.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## What it does

```text
 immich-go-import.sh — import a mirrorless-camera SD card into Immich via immich-go.
                       Phase 2. Idempotent (immich-go dedups by checksum on the server).

 WHY THIS EXISTS: a camera SD card has NO auto-backup — nothing pulls photos off
 it the way a phone auto-uploads. The workflow is: copy the card off to an SSD
 first (so you have the originals), THEN import that copy into Immich. This script
 does the import step; see immich-go-import.md for the full SD → SSD → Immich flow.

 What it does:
   1. Validates env (server URL, API key, card/source folder).
   2. Runs `immich-go upload from-folder` with --manage-raw-jpeg so a RAW+JPEG
      pair shot together is STACKED as one asset (not two duplicates).
   3. Re-running is safe: immich-go skips assets already on the server (checksum).

 Docs:
   immich-go:        https://github.com/simulot/immich-go
   upload from-folder: https://github.com/simulot/immich-go/blob/main/docs/upload.md
   Immich API keys:  https://docs.immich.app/features/command-line-interface (and Account Settings)

 Usage:
   IMMICH_SERVER=https://photos.example.com \
   IMMICH_API_KEY=xxxxxxxx \
   CARD_PATH=/mnt/ssd/ingest/2026-06-26 \
     ./immich-go-import.sh

   # dry-run first to see what WOULD upload:
   DRY_RUN=1 CARD_PATH=... ./immich-go-import.sh
```

## Environment / variables referenced

`ARGS`, `CARD_PATH`, `DRY_RUN`, `IMMICH_API_KEY`, `IMMICH_SERVER`

## See also

- [`flac-to-alac-inplace.sh`](flac-to-alac-inplace-sh.md)
- [`install-ipod-tools-cachyos.sh`](install-ipod-tools-cachyos-sh.md)
- [`install-slskd-native.sh`](install-slskd-native-sh.md)
- [`nas-music-to-alac-mirror.sh`](nas-music-to-alac-mirror-sh.md)
- [`rclone-manual-copy.sh`](rclone-manual-copy-sh.md)
- [`rclone-seedbox-mount.sh`](rclone-seedbox-mount-sh.md)
- [`rclone-seedbox-watchdog.sh`](rclone-seedbox-watchdog-sh.md)
- [`readarr-copy-to-cwa-ingest.sh`](readarr-copy-to-cwa-ingest-sh.md)
- [`seedbox-sync.sh`](seedbox-sync-sh.md)
- [`verify-tailscale-seedbox.sh`](verify-tailscale-seedbox-sh.md)
- [`window-maint-unpackerr-rclone.sh`](window-maint-unpackerr-rclone-sh.md)
- [Media pipeline scripts](index.md) · [All scripts](../index.md)
