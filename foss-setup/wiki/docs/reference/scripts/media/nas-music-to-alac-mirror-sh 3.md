# `nas-music-to-alac-mirror.sh`

> Maintain ~/Music on the rig as an iPod-playable MIRROR of the NAS master library.

**Path:** `foss-setup/scripts/media/nas-music-to-alac-mirror.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## What it does

```text
 Maintain ~/Music on the rig as an iPod-playable MIRROR of the NAS master library.
   NAS /volume1/music (FLAC + MP3/AAC, read-only mount)  ->  ~/Music
   FLAC  -> ALAC (.m4a, 16-bit, <=48kHz)   [iPod Classic can't play FLAC/hi-res]
   MP3/AAC/M4A -> copied verbatim           [already iPod-native]
 Incremental (skips up-to-date targets), prunes orphans (tracks removed from NAS).
 Read-only on the NAS; only ever writes/deletes under ~/Music.

 SAFETY: if the NAS source looks empty/unavailable, ABORT before pruning — a NAS
 blip must never wipe the mirror.
```

## Environment / variables referenced

`DST`, `LOCK`, `LOG`, `SRC`

## See also

- [`flac-to-alac-inplace.sh`](flac-to-alac-inplace-sh.md)
- [`immich-go-import.sh`](immich-go-import-sh.md)
- [`install-ipod-tools-cachyos.sh`](install-ipod-tools-cachyos-sh.md)
- [`install-slskd-native.sh`](install-slskd-native-sh.md)
- [`rclone-manual-copy.sh`](rclone-manual-copy-sh.md)
- [`rclone-seedbox-mount.sh`](rclone-seedbox-mount-sh.md)
- [`rclone-seedbox-watchdog.sh`](rclone-seedbox-watchdog-sh.md)
- [`readarr-copy-to-cwa-ingest.sh`](readarr-copy-to-cwa-ingest-sh.md)
- [`seedbox-sync.sh`](seedbox-sync-sh.md)
- [`verify-tailscale-seedbox.sh`](verify-tailscale-seedbox-sh.md)
- [`window-maint-unpackerr-rclone.sh`](window-maint-unpackerr-rclone-sh.md)
- [Media pipeline scripts](index.md) · [All scripts](../index.md)
