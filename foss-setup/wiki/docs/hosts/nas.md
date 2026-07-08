# nas — Synology DS920+

Storage and the data-heavy always-on services. Everything irreplaceable
ultimately lives (or lands) here.

| | |
|---|---|
| **Hardware** | Synology DS920+ — Celeron J4125 (Intel Quick Sync), 4 GB RAM (**20 GB upgrade pending** — Crucial CT16G4SFD8266) |
| **OS** | DSM 7.x (appliance — do not fight it) |
| **IP / aliases** | `192.168.10.4` · SSH alias `nas` · Tailscale `nas.*.ts.net` |
| **Power** | 24/7, ~35–45 W |
| **Access** | DSM web UI (2FA); `ssh nas` (key-based; **sudo needs a password** — vault slot, so agents can't inspect Docker without it) |

## Storage layout (three Basic volumes, ~42 TB, no parity)

| Volume | Size | Role |
|---|---|---|
| `/volume1` | ~14.6 TB | Music, Books, **Tier 1** (Immich, Paperless data), Docker, rclone mounts, manual lane |
| `/volume2` | ~10.9 TB | Movies only |
| `/volume3` | ~16.4 TB | TV only |

A single drive failure loses that whole volume — that trade is intentional;
Tier 1 rides snapshots + off-site backup (pending: B2). Authoritative spec:
`configs/nas/SCHEMA.md`.

## What runs here (Container Manager)

- **Immich** (photos — the canonical instance; `:2283`, <https://immich.tabaska.us>) with OpenVINO ML + Quick Sync
- **Plex** (native package) + media libraries
- **Calibre-Web-Automated** (`:8083`, LAN/VPN-only by design)
- **media-automation stack**: Sonarr, Radarr, Lidarr, Readarr (+ rreading-glasses), Prowlarr, FlareSolverr, Soularr, beets, Unpackerr — the full *arr suite, co-located with the library
- **adguard-nas** — the secondary DNS (`:53`, UI `:3000`); must stay up for the fail-open chain (pending: dns-02 re-verify)
- **rclone SFTP mount** of the seedbox: `/volume1/mounts/seedbox-files`, bound into every download-touching container at `/seedbox` — *a dropped mount silently stalls every import*; a watchdog remounts it (Task Scheduler, every 5 min)

## Maintenance channel

**DSM UI only** — the NAS is deliberately **not** Ansible-managed (DSM resets
system files on updates). Its restore path is DSM Configuration Backup +
Hyper Backup + the compose files in `configs/nas/`. Scheduled jobs live in
**DSM Task Scheduler** (rclone mount at boot, mount watchdog, Immich pg_dump
— pending: nas-08 schedule).

## Capacity rule

At 4 GB RAM the NAS is in **limp mode**: Immich (ML capped) + Plex + CWA +
the *arr stack only. Paperless / Frigate / Tdarr / Dependency-Track land here
**only after** the 20 GB upgrade.

## Failure blast radius

NAS down: photos, all media serving and acquisition, books, the secondary
DNS, and every backup target. Clients keep internet via the DNS chain.
