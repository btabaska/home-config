# `install-ipod-tools-cachyos.sh`

> install-ipod-tools-cachyos.sh

**Path:** `foss-setup/scripts/media/install-ipod-tools-cachyos.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## Synopsis

```
Safe to re-run: uses `pacman -S --needed`; AUR steps are skipped if the helper
```

## What it does

```text
 install-ipod-tools-cachyos.sh

 Idempotent install of the iPod Classic sync toolchain on CachyOS (Arch-based):
   - rhythmbox  : simplest iPod sync (built-in libgpod-backed iPod support)
   - libgpod    : the library that reads/writes Apple's iTunesDB (+ ipod tools)
   - gtkpod     : power-user GUI (aging but handy for DB surgery)   [optional]
   - hfsprogs   : fsck/mkfs for HFS+ iPods formatted on a Mac (AUR)  [optional]

 DECISION (see foss-setup-plan-2 §2 "iPod Classic"): keep Apple firmware +
 libgpod tooling so car/USB-controller integration stays intact. Music master
 stays on the NAS (Navidrome's library); the iPod is a reproducible copy.

 Safe to re-run: uses `pacman -S --needed`; AUR steps are skipped if the helper
 or package is already present.

 Refs:
   - ArchWiki iPod:        https://wiki.archlinux.org/title/IPod
   - libgpod project:      https://github.com/gtkpod/libgpod
   - Rhythmbox:            https://wiki.gnome.org/Apps/Rhythmbox

 Usage:
   ./install-ipod-tools-cachyos.sh                 # repo tools only
   WITH_GTKPOD=1 ./install-ipod-tools-cachyos.sh    # also install gtkpod
   WITH_HFSPROGS=1 ./install-ipod-tools-cachyos.sh  # also build hfsprogs (AUR)
```

## Environment / variables referenced

`WITH_GTKPOD`, `WITH_HFSPROGS`

## See also

- [`flac-to-alac-inplace.sh`](flac-to-alac-inplace-sh.md)
- [`immich-go-import.sh`](immich-go-import-sh.md)
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
