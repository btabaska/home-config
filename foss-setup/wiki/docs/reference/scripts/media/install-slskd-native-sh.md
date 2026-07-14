# `install-slskd-native.sh`

> Install slskd as a native binary on the Bytesized seedbox (Betty).

**Path:** `foss-setup/scripts/media/install-slskd-native.sh` · **Category:** [Media pipeline](index.md) · **Type:** Bash

## What it does

```text
 Install slskd as a native binary on the Bytesized seedbox (Betty).

 Rootless Docker cannot expose Soulseek peer port 50300 — use this instead.
 Run from your MacBook after SSH to seedbox works:
   scp scripts/media/install-slskd-native.sh seedbox:~/install-slskd-native.sh
   ssh seedbox 'bash ~/install-slskd-native.sh'

 Credentials: edit ~/slskd-native/.env (see configs/seedbox/slskd-native.example.env)
```

## Environment / variables referenced

`APP_DIR`, `BIN`, `BIN_DIR`, `ENV_FILE`, `REPO_EXAMPLE`, `SCRIPT_DIR`, `SLSKD_HTTP_IP`, `SLSKD_VERSION`, `SLSKD_WEB_PASSWORD`, `SLSKD_WEB_USERNAME`, `XDG_RUNTIME_DIR`

## See also

- [`flac-to-alac-inplace.sh`](flac-to-alac-inplace-sh.md)
- [`immich-go-import.sh`](immich-go-import-sh.md)
- [`install-ipod-tools-cachyos.sh`](install-ipod-tools-cachyos-sh.md)
- [`nas-music-to-alac-mirror.sh`](nas-music-to-alac-mirror-sh.md)
- [`rclone-manual-copy.sh`](rclone-manual-copy-sh.md)
- [`rclone-seedbox-mount.sh`](rclone-seedbox-mount-sh.md)
- [`rclone-seedbox-watchdog.sh`](rclone-seedbox-watchdog-sh.md)
- [`readarr-copy-to-cwa-ingest.sh`](readarr-copy-to-cwa-ingest-sh.md)
- [`seedbox-sync.sh`](seedbox-sync-sh.md)
- [`verify-tailscale-seedbox.sh`](verify-tailscale-seedbox-sh.md)
- [`window-maint-unpackerr-rclone.sh`](window-maint-unpackerr-rclone-sh.md)
- [Media pipeline scripts](index.md) · [All scripts](../index.md)
