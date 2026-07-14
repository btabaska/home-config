# `rclone-seedbox-mount.sh`

> persistent rclone SFTP mount of the seedbox files

**Path:** `foss-setup/scripts/media/rclone-seedbox-mount.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## What it does

```text
 ==============================================================================
 rclone-seedbox-mount.sh — persistent rclone SFTP mount of the seedbox files
 ==============================================================================
 Phase 2. Runs ON THE NAS (DS920+). Mounts the seedbox's completed-downloads
 folder so the home *arr stack can READ finished downloads for import:

     seedbox:/home/hd34/btabaska/files  ->  /volume1/mounts/seedbox-files

 The *arr containers bind this host path to /seedbox. Their Remote Path
 Mapping (/home/hd34/btabaska/files/ -> /seedbox/) makes the path Deluge
 reports resolve here.

 !!! A DROPPED OR STALE MOUNT SILENTLY STALLS ALL IMPORTS !!!
 If this FUSE mount goes away, the bind target becomes an empty dir and every
 *arr import quietly does nothing (no error). That is why:
   - this unit/task starts at boot, and
   - rclone-seedbox-watchdog.sh re-runs it if the mountpoint is empty/stale.

 DSM SETUP (Synology has no systemd): Control Panel -> Task Scheduler ->
   Create -> Triggered Task -> User-defined script, Event = Boot-up, User = root,
   Command = /volume1/scripts/media/rclone-seedbox-mount.sh

 SAFETY CONTRACT:
   - This script ONLY mounts. It NEVER tears down a live mount.
   - Stale-mount detection is the watchdog's job.
   - Running this script when already mounted is a safe no-op (exit 0).

 Docs: https://rclone.org/commands/rclone_mount/  |  https://rclone.org/sftp/
 ==============================================================================
```

## Environment / variables referenced

`CACHE_DIR`, `COMPOSE_FILE`, `DOCKER`, `HEALTH_FILE`, `LOG`, `MOUNTPOINT`, `RCLONE`, `RCLONE_CONF`, `REMOTE`, `WAIT_SECS`

## See also

- [`flac-to-alac-inplace.sh`](flac-to-alac-inplace-sh.md)
- [`immich-go-import.sh`](immich-go-import-sh.md)
- [`install-ipod-tools-cachyos.sh`](install-ipod-tools-cachyos-sh.md)
- [`install-slskd-native.sh`](install-slskd-native-sh.md)
- [`nas-music-to-alac-mirror.sh`](nas-music-to-alac-mirror-sh.md)
- [`rclone-manual-copy.sh`](rclone-manual-copy-sh.md)
- [`rclone-seedbox-watchdog.sh`](rclone-seedbox-watchdog-sh.md)
- [`readarr-copy-to-cwa-ingest.sh`](readarr-copy-to-cwa-ingest-sh.md)
- [`seedbox-sync.sh`](seedbox-sync-sh.md)
- [`verify-tailscale-seedbox.sh`](verify-tailscale-seedbox-sh.md)
- [`window-maint-unpackerr-rclone.sh`](window-maint-unpackerr-rclone-sh.md)
- [Media pipeline scripts](index.md) · [All scripts](../index.md)
