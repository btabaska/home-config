# Seedbox & music reference

The download/seed edge ("Betty") and the music-acquisition pipeline. In the current
architecture the seedbox runs **only Deluge** (download + seed) plus a **native slskd**
binary; the full \*arr stack and the Soularr/beets music tooling run on the **NAS**,
reaching Betty over its Deluge API and an rclone SFTP mount.

| Page | |
|---|---|
| [Music pipeline](music-pipeline.md) | MusicSeerr → Lidarr → Soularr → slskd → beets |
| [Deluge queue hygiene](deluge-queue-hygiene.md) | Betty Deluge labels, the reaper, and the \*arr queue-clog fix |
| [Provider comparison (2026)](provider-comparison.md) | Why Bytesized "Betty" — managed-seedbox decision record |
| [Decommission the old NAS torrent stack](decommission-old-nas-torrent.md) | Retiring on-NAS qBittorrent + Gluetun + dual-LAN policy routing |

_4 pages._

!!! note "Superseded designs (retired)"
    The old "everything on the seedbox" layout — `arr-suite-wiring.md`,
    `lidarr-slskd-soularr.md`, and the `music-pipeline-soulseek.md` redirect — has been
    superseded by the split architecture above (Betty = Deluge + native slskd; \*arr +
    Soularr + beets on the NAS). Those source docs are retired; use the pages here and the
    NAS `reference/nas/media-automation.md` page instead.
