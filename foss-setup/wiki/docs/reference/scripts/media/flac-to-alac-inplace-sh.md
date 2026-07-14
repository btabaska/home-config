# `flac-to-alac-inplace.sh`

> Convert FLAC -> ALAC (Apple Lossless .m4a) IN PLACE under a music dir, for the

**Path:** `foss-setup/scripts/media/flac-to-alac-inplace.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## Synopsis

```
MUSIC_DIR=~/Music ./flac-to-alac-inplace.sh          # dry-run (lists)
```

## What it does

```text
 Convert FLAC -> ALAC (Apple Lossless .m4a) IN PLACE under a music dir, for the
 stock-firmware iPod Classic (which can't play FLAC). On successful, verified
 conversion the source FLAC is DELETED. MP3/AAC are left untouched (iPod-native).

 iPod Classic ALAC limits: 16-bit, <=48 kHz. So: always output 16-bit; resample
 to 48 kHz only if the source is >48 kHz (hi-res). Tags + embedded cover art are
 carried across. Idempotent/resumable: skips a track whose .m4a already exists.

 SAFETY GATE: refuses to run unless the NAS master copy has been verified — the
 caller must create the sentinel file (see MIGRATION_OK below). This exists so the
 FLAC (deleted here) is never removed before its master copy is confirmed on the NAS.

 Usage:  MUSIC_DIR=~/Music ./flac-to-alac-inplace.sh          # dry-run (lists)
         MUSIC_DIR=~/Music APPLY=1 ./flac-to-alac-inplace.sh  # convert + delete FLAC
```

## Environment / variables referenced

`APPLY`, `LOG`, `MIGRATION_OK`, `MUSIC_DIR`, `SENTINEL`

## See also

- [`immich-go-import.sh`](immich-go-import-sh.md)
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
