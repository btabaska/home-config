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
- **tailscaled** (userspace) + **syncthing** — systemd user units / `~/.startup`

Nothing else. No *arr apps, no sync agents — the full *arr stack lives on the
[NAS](nas.md). qBittorrent was **retired 2026-07-17** (fix-21/L9: idle since
Jun 27 with a public WebUI).

## Network exposure (fix-21 lockdown, 2026-07-17)

Quality-gate H2/M25 found Deluge RPC/web, qBittorrent and slskd all bound to
the **public** shared IP, with arr/soularr passwords crossing the WAN in
cleartext. Since the lockdown:

- Deluge RPC `3254`, deluge-web `5945`, slskd `5030` bind **127.0.0.1 only**;
  slskd HTTPS `5031` is disabled. Public IP exposes just sshd + the peer ports
  (Deluge `51867` TCP/UDP via `random_port`, Soulseek `50300`).
- Consumers reach them **over the tailnet** at `100.119.134.94` — userspace
  tailscaled forwards inbound tailnet connections to loopback. Repointed:
  sonarr/radarr/lidarr/readarr/whisparr Deluge client **and Remote Path
  Mapping host**, soularr `host_url`, and the mini Caddy vhosts
  (`deluge.tabaska.us` → `:5945` — it had been proxying `:8112`, which is
  **another tenant's** Deluge on this shared box, a false-green Kuma monitor).
- The NAS needs its Tailscale package in **TUN mode** for outbound tailnet TCP
  (see `configs/nas/tailscale/`); DSM task 13 re-asserts it daily.
- Config mirrors + persistence details: `configs/host/seedbox/README.md`.
  Guarded by `verification/checks.d/seedbox.yaml` (public-port sweep, loopback
  binds, sonarr→Deluge e2e, slskd LoggedIn e2e, service manifest) — runbook:
  [seedbox exposure](../runbooks/seedbox-exposure.md).

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
    `ssh seedbox` works (Tailscale SSH from the laptop; mini's verification
    runner uses the public `betty.bysh.me` sshd — the tailnet ACL only allows
    the laptop). Kuma watches the Deluge and slskd web UIs via
    `deluge.tabaska.us` / `slskd.tabaska.us`; the `seedbox-*` verification
    checks probe the consumer paths end to end (sonarr's own download-client
    test, slskd Soulseek login); the NAS rclone mount showing fresh files is
    the functional end-to-end signal. There is no root, so host-level
    monitoring is the provider's job.
