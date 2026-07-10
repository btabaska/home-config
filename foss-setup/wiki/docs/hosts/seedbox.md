# seedbox — "Betty" (Bytesized, off-site)

A managed off-site box that keeps **all P2P traffic off the home network**.
The ISP never sees a swarm.

| | |
|---|---|
| **Provider** | Bytesized "Stream +3" AppBox — 3000 GB, **no root**, shared IP `185.162.184.38` |
| **Home dir** | `/home/hd34/btabaska` |
| **Access** | Tailscale SSH as `btabaska` — working (`ssh seedbox` → `seedbox.tailb31641.ts.net`; the early tailnet-ACL block was fixed) |
| **Power / uptime** | Managed by the provider, always on |

## What runs here

- **Deluge** (torrents) — sorts completed downloads into label folders under
  `files/`: `tv`, `movies`, `music`, `books`, `manual`
- **slskd** (Soulseek) — **native binary**, not Docker; writes to `files/slskd/`
- **deluge-reaper** — daily 05:00 cron (`~/scripts/deluge-reaper.py --live`,
  repo copy `configs/host/seedbox/deluge-reaper.py`): prunes dead/aged
  torrents per label rules

Nothing else. No *arr apps, no qBittorrent, no sync agents — the full *arr
stack lives on the [NAS](nas.md).

## How files reach home

The NAS holds a persistent **rclone SFTP mount**:
`seedbox:/home/hd34/btabaska/files → /volume1/mounts/seedbox-files`, bound
into every download-touching NAS container at `/seedbox` (`:rslave`). Each
*arr has a Remote Path Mapping `/home/hd34/btabaska/files/ → /seedbox/`.
Imports are cross-filesystem **copies** ("Remove Completed" stays OFF so
seeding continues). One scheduled job only: the manual lane
(`files/manual → /volume1/manual`, every 15 min, re-run-safe).

If imports stall fleet-wide, suspect the mount first — see
`scripts/media/rclone-seedbox-watchdog.sh`.

## Maintenance channel

**User-space only** — no root, so only the things in `$HOME` are ours
(Deluge config, slskd, cron). Not Ansible-managed beyond user-space. Provider
panel handles the OS. Keys-only SSH; the provider box is the one
internet-exposed surface, treat credentials accordingly.

!!! note "Liveness signals"
    `ssh seedbox` works (Tailscale). Kuma watches the Deluge and slskd web
    UIs via `deluge.tabaska.us` / `slskd.tabaska.us`; the NAS rclone mount
    showing fresh files is the functional end-to-end signal. There is no
    root, so host-level monitoring is the provider's job.
