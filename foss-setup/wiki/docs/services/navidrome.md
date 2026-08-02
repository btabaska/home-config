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

Navidrome is the self-hosted music-streaming server (Subsonic/OpenSubsonic API) running on `mini` from `foss-setup/configs/docker-stack/stacks/navidrome/compose.yaml` as `deluan/navidrome:0.62.0`, fronted by Caddy at https://music.tabaska.us and also exposed directly on `4533` for LAN Subsonic clients (Symfonium/Amperfy). It reads the NAS music library read-only via `${MUSIC_FOLDER}` (`/mnt/nas/music`, a `vers=3.0` CIFS mount of `//192.168.10.4/music`) at `/music`, while its own SQLite DB lives under `./data` and nightly DB backups land in `./backup` (fix-37/M15, 2026-07-18: `ND_BACKUP_SCHEDULE` alone silently no-ops — Navidrome logs "Periodic backup is DISABLED" unless `ND_BACKUP_PATH` is ALSO set, so the intended nightly backup never ran until the path + `./backup:/backup` mount were added; restic picks the dir up via `/opt/stacks`, and the `navidrome-backup-fresh` check requires a <26h backup file on disk). The container runs as `${PUID}:${PGID}` (1000:1000, which must own `./data`). The load-bearing config decisions are `ND_SCANNER_SCHEDULE="0"` — Navidrome's built-in periodic scanner is DISABLED as of **fix-49** — and `ND_SCANNER_WATCHERWAIT=0` (the CIFS fs-watcher is unreliable and dies on mount EBADF). Scanning is instead driven by a **mount-gated host timer** on mini (`foss-setup/configs/host/mini/navidrome-scan/`: `navidrome-scan.timer` fires every 15 min → `navidrome-scan-gate.sh` → the Subsonic `startScan` API against the running server, single sqlite writer). The gate REFUSES to scan unless the read-only CIFS music root is actually populated, so a transient empty read can no longer mass-flag the whole library missing — the 2026-08-01 SC1 outage, where an hourly quick scan saw the root momentarily empty and greyed out all 3495 tracks — and it triggers a FULL scan to self-heal if it ever finds the library already mass-flagged while the mount is healthy. New tracks ingested onto the NAS by MeTube/Pinchflat into `/volume1/music/YouTube` are picked up on the next gated scan.

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
- **The WHOLE library is greyed out / unplayable — every track shows as missing in the UI — while the container is "healthy" and https://music.tabaska.us/ping returns 200 (the 2026-08-01 SC1 outage class).** — `missing=1` on a media_file row is exactly what greys it out. A mass-flag has one of two causes, both fixable without touching data (the files are fine on the NAS). (1) A bad root `.ndignore`: `/mnt/nas/music/.ndignore` MUST contain the escaped pattern `\#recycle` (one line). `.ndignore` is gitignore syntax where a leading `#` is a COMMENT, so a bare `#recycle` = zero patterns = an EMPTY .ndignore = "skip this whole folder" at the library root. Rewrite it on the NAS side (the mini mount is read-only): `printf '\\#recycle\n' | ssh nas 'cat > /volume1/music/.ndignore'` — or just run `scripts/nas/ensure-navidrome-music-ignore.sh` on the NAS. (2) A scan that observed the CIFS root as momentarily empty. Either way, quick scans NEVER clear a missing flag — you need a FULL scan: `ssh mini 'cd /opt/stacks/navidrome && docker compose stop navidrome && docker compose run --rm -T navidrome scan -f && docker compose up -d navidrome'`, then confirm `docker exec navidrome sqlite3 -readonly /data/navidrome.db "select count(*),sum(missing) from media_file"` shows missing back at 0. The mount-gated `navidrome-scan.timer` now self-heals this within 15 min; checks `navidrome-library-present` (crit) + `navidrome-scan-integrity` (crit) page on recurrence.
- **New music never appears in Navidrome (and `navidrome-scan-fresh` is stale).** — Navidrome's built-in periodic scanner is intentionally DISABLED (`ND_SCANNER_SCHEDULE: "0"`, fix-49); scans are driven by the mount-gated `navidrome-scan.timer` on mini. Check it: `ssh mini 'systemctl status navidrome-scan.timer; journalctl -u navidrome-scan.service --no-pager -n 5'`. A `GATE_SKIP empty-or-short` line means the CIFS music root read empty (NAS/mount problem — fix the mount first, do NOT re-enable the built-in scanner). A `SCAN_TRIGGERED` line means it is working. Re-arm with `sudo systemctl enable --now navidrome-scan.timer`. See `foss-setup/configs/host/mini/navidrome-scan/README.md`.
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
