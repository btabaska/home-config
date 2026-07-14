# `seedbox-sync.sh`

> ⚠️ LEGACY — SUPERSEDED by the NAS *arr stack (2026 architecture).

**Path:** `foss-setup/scripts/media/seedbox-sync.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## What it does

```text
 ⚠️ LEGACY — SUPERSEDED by the NAS *arr stack (2026 architecture).

 The current model does NOT use a scheduled seedbox→NAS copy for tv/movies/music.
 Betty runs Deluge only; the *arr stack on the NAS imports via a live rclone mount
 (rclone-seedbox-mount.sh). The ONLY scheduled rclone job is rclone-manual-copy.sh
 (manual lane → /volume1/manual).

 This script is kept for reference or one-off bulk migrations. Paths below match the
 three-volume layout (nas-storage-schema.md) if you still need a cron-pull.

 seedbox-sync.sh — pull finished, named media from the off-site seedbox to the NAS via rclone+SFTP.
                   Phase 2. Runs ON THE NAS (the puller). Designed for cron. Idempotent.

 Why copy (not sync): the seedbox keeps seeding the original files for ratio. We pull a COPY down
 to the NAS library; we never mirror-delete the seedbox. `rclone copy` skips already-transferred
 files (size + mod-time), so re-running is cheap and safe.
   rclone copy:  https://rclone.org/commands/rclone_copy/
   rclone sync:  https://rclone.org/commands/rclone_sync/   (NOT used here — it would delete)
   SFTP backend: https://rclone.org/sftp/

 Transfer rides the Tailscale tailnet (set the SFTP host in rclone.conf to the seedbox's
 Tailscale name/IP) so nothing is exposed to the internet. SFTP is encrypted regardless.

 GUI ALTERNATIVE — Syncthing:
   Prefer a GUI / continuous push instead of cron-pull? Run Syncthing on BOTH the seedbox and the
   NAS. On the seedbox share the media folder as **Send Only**; on the NAS set the same folder
   **Receive Only** + file versioning. Syncthing then continuously mirrors finished files down with
   no scripting. Use one or the other, not both, for a given folder.
     Getting started: https://docs.syncthing.net/intro/getting-started.html
     Folder types:    https://docs.syncthing.net/users/foldertypes.html

 ---------------------------------------------------------------------------------------------------
 Setup (once, on the NAS):
   1. Install rclone:        https://rclone.org/install/
   2. Create the remote:     cp configs/seedbox/rclone.conf.example ~/.config/rclone/rclone.conf
                             # edit placeholders, then: chmod 600 ~/.config/rclone/rclone.conf
   3. Test it:               rclone lsd seedbox:

 Run (manual dry-run first!):
   DRY_RUN=1 ./seedbox-sync.sh
   ./seedbox-sync.sh

 Cron (every 15 min, log to file) — LEGACY only; do not run alongside *arr import:
   */15 * * * * RCLONE_REMOTE=seedbox /volume1/scripts/media/seedbox-sync.sh >> /var/log/seedbox-sync.log 2>&1

 A lockfile prevents overlapping runs (a slow pull won't stack up under cron).
```

## Environment / variables referenced

`BWLIMIT`, `CHECKERS`, `DRY_RUN`, `LOCAL_MOVIES`, `LOCAL_MUSIC`, `LOCAL_TV`, `LOCKFILE`, `MIN_AGE`, `RCLONE_ARGS`, `RCLONE_REMOTE`, `REMOTE_MOVIES`, `REMOTE_MUSIC`, `REMOTE_TV`, `SYNC_MUSIC`

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
- [`verify-tailscale-seedbox.sh`](verify-tailscale-seedbox-sh.md)
- [`window-maint-unpackerr-rclone.sh`](window-maint-unpackerr-rclone-sh.md)
- [Media pipeline scripts](index.md) · [All scripts](../index.md)
