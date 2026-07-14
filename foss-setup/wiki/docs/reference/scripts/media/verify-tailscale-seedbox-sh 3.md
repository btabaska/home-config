# `verify-tailscale-seedbox.sh`

> confirm the off-site seedbox is on the tailnet and the home

**Path:** `foss-setup/scripts/media/verify-tailscale-seedbox.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## What it does

```text
 verify-tailscale-seedbox.sh — confirm the off-site seedbox is on the tailnet and the home
                               hosts can reach the *arr apps over it. Phase 2.

 Managed seedboxes are SHARED servers with NO root and NO TUN device, so you almost always run
 Tailscale in **userspace networking** mode from your home dir (static binaries + custom socket).
 This script auto-detects that socket and reports what's reachable. Run it ON THE SEEDBOX.

 Refs:
   Userspace networking (no root/TUN): https://tailscale.com/kb/1112/userspace-networking/
   Static binaries (download):         https://pkgs.tailscale.com/stable/#static
   tailscale status / ping:            https://tailscale.com/kb/1080/cli/

 First-time install on a seedbox (userspace mode), for reference:
   mkdir -p ~/tailscale && cd ~/tailscale
   curl -fsSL "https://pkgs.tailscale.com/stable/tailscale_<VER>_amd64.tgz" -o ts.tgz
   tar --strip-components=1 -xzf ts.tgz tailscale_<VER>_amd64/tailscale tailscale_<VER>_amd64/tailscaled
   ./tailscaled --tun=userspace-networking \
                --state=$HOME/tailscale/tailscaled.state \
                --socket=$HOME/tailscale/tailscaled.sock --port=41641 &
   ./tailscale --socket=$HOME/tailscale/tailscaled.sock up   # opens an auth URL
 (Wire that tailscaled command into a user systemd unit or the provider's "boot script" so it
  survives reboots — see the userspace networking KB.)
```

## Environment / variables referenced

`DELUGE_PORT`, `DELUGE_WEB_PORT`, `PEERS`, `SELF_IP`, `STATUS`, `TS_BIN`, `TS_SOCKET`

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
- [`window-maint-unpackerr-rclone.sh`](window-maint-unpackerr-rclone-sh.md)
- [Media pipeline scripts](index.md) · [All scripts](../index.md)
