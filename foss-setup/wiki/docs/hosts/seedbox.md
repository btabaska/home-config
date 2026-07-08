# seedbox — "Betty" (Bytesized, off-site)

A managed off-site box that keeps **all P2P traffic off the home network**.
The ISP never sees a swarm.

| | |
|---|---|
| **Provider** | Bytesized "Stream +3" AppBox — 3000 GB, **no root**, shared IP `185.162.184.38` |
| **Home dir** | `/home/hd34/btabaska` |
| **Access** | Tailscale SSH as `btabaska` — **currently blocked by the tailnet ACL** (pending: human queue — add an SSH rule in the Tailscale admin console) |
| **Power / uptime** | Managed by the provider, always on |

## What runs here

- **Deluge** (torrents) — sorts completed downloads into label folders under
  `files/`: `tv`, `movies`, `music`, `books`, `manual`
- **slskd** (Soulseek) — **native binary**, not Docker; writes to `files/slskd/`

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

!!! warning "Currently unverifiable"
    Until the Tailscale ACL is fixed, nothing on Betty can be inspected or
    managed from the operator's machines. The NAS mount showing files is the
    only liveness signal.
