# navidrome

Navidrome — self-hosted music streaming (Subsonic/OpenSubsonic API)

| | |
|---|---|
| **Host** | [mini](../hosts/mini.md) |
| **URL** | https://music.tabaska.us |
| **Source** | `foss-setup/configs/docker-stack/stacks/navidrome/compose.yaml` |
| **Notes** | Subsonic-compatible music streaming. |
| **Upstream docs** | <https://www.navidrome.org/docs/installation/docker/> |

## About

Navidrome is the self-hosted music-streaming server (Subsonic/OpenSubsonic API) running on `mini` from `foss-setup/configs/docker-stack/stacks/navidrome/compose.yaml` as `deluan/navidrome:0.62.0`, fronted by Caddy at https://music.tabaska.us and also exposed directly on `4533` for LAN Subsonic clients (Symfonium/Amperfy). It reads the NAS music library read-only via `${MUSIC_FOLDER}` (`/mnt/nas/music`, a `vers=3.0` CIFS mount of `//192.168.10.4/music`) at `/music`, while its own SQLite DB lives under `./data` and nightly DB backups land in `./backup` (fix-37/M15, 2026-07-18: `ND_BACKUP_SCHEDULE` alone silently no-ops — Navidrome logs "Periodic backup is DISABLED" unless `ND_BACKUP_PATH` is ALSO set, so the intended nightly backup never ran until the path + `./backup:/backup` mount were added; restic picks the dir up via `/opt/stacks`, and the `navidrome-backup-fresh` check requires a <26h backup file on disk). The container runs as `${PUID}:${PGID}` (1000:1000, which must own `./data`). The load-bearing config decisions are `ND_SCANNER_SCHEDULE="@every 1h"` (the 0.62 new-scanner key — the legacy `ND_SCANSCHEDULE`/`ND_SCANNER_WATCHERWAIT` semantics changed) driving a periodic full scan, and `ND_SCANNER_WATCHERWAIT=0` disabling the fs-watcher because it is unreliable over CIFS. New tracks are ingested onto the NAS by MeTube/Pinchflat into `/volume1/music/YouTube` and picked up on the next hourly scan.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `navidrome` | `deluan/navidrome:0.62.0` | `4533:4533` |

## Volumes

| Service | Volume |
|---|---|
| `navidrome` | `./data:/data` |
| `navidrome` | `./backup:/backup` |
| `navidrome` | `${MUSIC_FOLDER:?set MUSIC_FOLDER to your music library path}:/music:ro` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `PUID`
- `PGID`
- `MUSIC_FOLDER`
- `TZ`
- `ND_BASEURL`
- `ND_BACKUP_SCHEDULE`
- `ND_BACKUP_COUNT`
- `ND_ENABLEINSIGHTSCOLLECTOR`

## Troubleshooting

- **Startup log shows "Periodic backup is DISABLED" even though ND_BACKUP_SCHEDULE and ND_BACKUP_COUNT are set.** — Navidrome arms the backup scheduler only when ND_BACKUP_PATH is also set — schedule+count alone is a silent no-op (this bit us for weeks, M15). compose.yaml pins ND_BACKUP_PATH=/backup with a ./backup:/backup mount; if the message reappears after a recreate, the env or mount regressed — restore them and confirm the log says "Scheduling periodic backup". First backup can be forced with docker exec navidrome /app/navidrome backup create; the navidrome-backup-fresh (crit) and navidrome-backup-armed checks page on recurrence.
- **New music never appears in Navidrome; logs show "Periodic scan is DISABLED".** — 0.62 ignores the legacy `ND_SCANSCHEDULE` key. Ensure `ND_SCANNER_SCHEDULE: "@every 1h"` is set in the compose environment (already the case in `stacks/navidrome/compose.yaml`), then `ssh mini 'cd /opt/stacks/navidrome && docker compose up -d'`. Confirm with `docker compose logs --tail 20` — you should see hourly "Scanner: Starting scan" / "Finished scanning all libraries" lines.
- **Relying on the filesystem watcher to pick up NAS-side writes, but new files still do not show up until much later (or scans error).** — The CIFS fs-watcher is unreliable — it misses NAS-side writes and dies on mount EBADF — so it is intentionally disabled via `ND_SCANNER_WATCHERWAIT: "0"`. Do not re-enable it; the hourly full scan is the source of truth. To force an immediate pickup, trigger a scan from the web UI (Settings) or restart the container.
- **After a NAS reboot the container throws EBADF / stale-handle errors reading `/music` and the library goes empty.** — The read-only music mount uses `x-systemd.automount` in `/etc/fstab` on mini (`//192.168.10.4/music /mnt/nas/music cifs ...,ro,nofail,_netdev,x-systemd.automount`) so the autofs mount self-heals on next access. If it is still stale, remount with `ssh mini 'sudo systemctl restart mnt-nas-music.automount'` (or `sudo mount /mnt/nas/music`), then restart Navidrome: `ssh mini 'cd /opt/stacks/navidrome && docker compose restart'`.

## Operations

```bash
ssh mini 'cd /opt/stacks/navidrome && docker compose ps'
ssh mini 'cd /opt/stacks/navidrome && docker compose logs --tail 50'
ssh mini 'cd /opt/stacks/navidrome && docker compose pull && docker compose up -d'
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
