# `window-maint-unpackerr-rclone.sh`

> ONE-SHOT windowed maintenance

**Path:** `foss-setup/scripts/media/window-maint-unpackerr-rclone.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## What it does

```text
 =============================================================================
 window-maint-unpackerr-rclone.sh — ONE-SHOT windowed maintenance
 =============================================================================
 Runs ON MINI (as btabaska — needs the `nas` ssh alias + known_hosts), drives
 the NAS over ssh. Scheduled for the 4-7AM ET window (08:00-11:00 UTC) via a
 systemd one-shot timer. Two gated phases, each verified, ntfy at every step —
 a silent failure at 4AM is the whole thing we're avoiding.

   PHASE A  clear the unpackerr wedge + apply its new healthcheck
            (docker rm -f unpackerr times out -> only a dockerd restart frees
            it; that bounces all NAS containers, hence the window).
   PHASE B  remount the rclone SFTP mount with the RAM-retuned flags
            (vfs-cache-mode full etc.) + restart the download-touching
            containers so they bind the fresh mount (the watchdog's pattern).

 Phase B only runs if Phase A fully verifies. Any failure -> high-priority
 ntfy naming the step, and the script stops (leaves the fleet in the last-good
 state for a human/next-session to inspect). DRY_RUN=1 does every read-only
 check + a labeled ntfy test but performs NO restart/remount.

 Self-cleaning: on success it disables its own timer so it can't re-fire.
 =============================================================================
```

## Environment / variables referenced

`BAD`, `BEFORE_COUNT`, `CACHEMODE`, `COMPOSE_DIR`, `DOCKER`, `DRY_RUN`, `EXPECT_CONTAINERS`, `FINAL`, `INSIDE`, `LOG`, `MOUNTPOINT`, `NAS_SSH`, `NAS_SUDO_PASSWORD`, `NTFY_TOKEN`

## See also

- [`flac-to-alac-inplace.sh`](flac-to-alac-inplace-sh.md)
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
- [Media pipeline scripts](index.md) · [All scripts](../index.md)
