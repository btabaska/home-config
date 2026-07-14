# `rclone-seedbox-watchdog.sh`

> self-heal the seedbox rclone mount

**Path:** `foss-setup/scripts/media/rclone-seedbox-watchdog.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## What it does

```text
 ==============================================================================
 rclone-seedbox-watchdog.sh — self-heal the seedbox rclone mount
 ==============================================================================
 Phase 2. Runs ON THE NAS (DS920+), every 5 min via DSM Task Scheduler.

 A dropped/stale rclone FUSE mount does NOT raise an error in the *arrs — it
 just makes /seedbox look empty, so imports silently stall forever. This
 watchdog detects that state and remounts.

 HEALTH LOGIC (two-strike before remount):
   Healthy  : mountinfo shows FUSE mount AND `ls` succeeds within 20 s
   Suspect  : mountinfo shows mount BUT `ls` times out/fails (SFTP may be
              slow — SFTP lag of up to 20 s happens on cold sessions over WAN)
   Unhealthy: not in mountinfo at all, OR suspect for 2+ consecutive cycles

 Two-strike rule prevents tearing down a live mount just because the SFTP
 session was slow. The state file /var/run/seedbox-watchdog.fail_count persists
 between invocations (cleared on success, incremented on Suspect).

 DSM SETUP: Control Panel -> Task Scheduler -> Create -> Scheduled Task ->
   User-defined script, User = root, repeat every 5 minutes,
   Command = /volume1/scripts/media/rclone-seedbox-watchdog.sh
 ==============================================================================
```

## Environment / variables referenced

`COMPOSE_FILE`, `DOCKER`, `FAIL_COUNT_FILE`, `FIND_TIMEOUT`, `HEALTH_FILE`, `LOCK_FILE`, `LOG`, `LS_TIMEOUT`, `MOUNTPOINT`, `MOUNT_SCRIPT`, `READ_TIMEOUT`

## See also

- [`flac-to-alac-inplace.sh`](flac-to-alac-inplace-sh.md)
- [`immich-go-import.sh`](immich-go-import-sh.md)
- [`install-ipod-tools-cachyos.sh`](install-ipod-tools-cachyos-sh.md)
- [`install-slskd-native.sh`](install-slskd-native-sh.md)
- [`nas-music-to-alac-mirror.sh`](nas-music-to-alac-mirror-sh.md)
- [`rclone-manual-copy.sh`](rclone-manual-copy-sh.md)
- [`rclone-seedbox-mount.sh`](rclone-seedbox-mount-sh.md)
- [`readarr-copy-to-cwa-ingest.sh`](readarr-copy-to-cwa-ingest-sh.md)
- [`seedbox-sync.sh`](seedbox-sync-sh.md)
- [`verify-tailscale-seedbox.sh`](verify-tailscale-seedbox-sh.md)
- [`window-maint-unpackerr-rclone.sh`](window-maint-unpackerr-rclone-sh.md)
- [Media pipeline scripts](index.md) · [All scripts](../index.md)
