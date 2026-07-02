# Music pipeline — MusicSeerr, Lidarr, Soularr, slskd, beets

Split architecture: **P2P stays on Betty** (Deluge + slskd). **Library and automation
stay on the NAS** (Lidarr, Soularr, beets). **Request portals on the Mac mini**
(Seerr = movies/TV, **MusicSeerr** = albums).

Seerr v3.x does **not** support Lidarr — use [MusicSeerr](https://musicseerr.com/) for
household album requests instead.

## Stack at a glance

```
Mac mini                          NAS (DS920+)                    Betty (seedbox)
────────                          ────────────                    ───────────────
Seerr :5055 ──Radarr/Sonarr──▶    Sonarr/Radarr/Prowlarr
MusicSeerr :8688 ──Lidarr───▶     Lidarr :8686 ──Deluge API──▶   Deluge (torrents)
                                  Soularr ──slskd API────────▶   slskd (Soulseek)
                                  beets (tag-only, optional)
                                        │
                                  /volume1/music ◀── rclone mount /seedbox/
                                        │
                                  Plex Music (NAS package)
Navidrome :4533 ◀── NFS /mnt/nas/music
```

## Request → download → library

```
MusicSeerr request → Lidarr (NAS) "Wanted"
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
   Torrent indexers                  Soularr (NAS)
   → Prowlarr → Deluge (Betty)       → slskd API (Betty, Tailscale)
   → files/music/                     → files/slskd/
         │                               │
         └───────────────┬───────────────┘
                         ▼
             rclone mount /seedbox/…  (NAS)
                         ▼
             Lidarr import → /volume1/music
                         ▼
             beets write (optional, tag-only)
                         ▼
             Plex Music · Navidrome · iPod sync
```

---

## Host placement

| Component | Host | Port / path | Role |
|-----------|------|-------------|------|
| **Deluge** | Betty | WebUI + daemon | Torrent P2P off-site; label `lidarr` → `files/music/` |
| **slskd** | Betty (native binary) | `:5030` API, `:50300` peers | Soulseek P2P; `~/slskd-native/.env` + user systemd service; downloads → `files/slskd/` |
| **Lidarr** | NAS | `:8686` | Music library manager; imports from `/seedbox/` |
| **Soularr** | NAS | headless | Lidarr ↔ remote slskd bridge |
| **beets** | NAS | `:8337` (profile `music-tags`) | Tag-only metadata on `/music` |
| **MusicSeerr** | Mac mini | `:8688` | Album request & discovery portal |
| **Seerr** | Mac mini | `:5055` | Movie/TV requests (not music) |
| **Navidrome** | Mac mini | `:4533` | Streams `/volume1/music` via NFS |
| **Plex Music** | NAS | `:32400` | Library root `/volume1/music` |

---

## Paths

**Betty** (`~/files/`):

```
tv/       movies/   music/   slskd/   books/   manual/
          ↑ Deluge label lidarr    ↑ slskd Soulseek downloads
```

**NAS** (container paths):

| Host path | Container | Purpose |
|-----------|-----------|---------|
| `/volume1/mounts/seedbox-files` | `/seedbox` | rclone SFTP mount of Betty `~/files/` |
| `/volume1/mounts/seedbox-files/music` | `/seedbox/music` | Torrent music for Lidarr import |
| `/volume1/mounts/seedbox-files/slskd` | `/seedbox/slskd` | Soulseek downloads for Lidarr import |
| `/volume1/music` | `/music` | Final library |

**Mac mini**:

| Path | Purpose |
|------|---------|
| `/mnt/nas/music` | NFS mount of NAS `/volume1/music` — Navidrome + MusicSeerr local playback |
| `/opt/stacks/musicseerr/` | MusicSeerr compose + config |

No scheduled copy for *arr music — live rclone mount + Lidarr import only.

---

## Rollout tasks

| Task | What |
|------|------|
| **nas-23** | Lidarr torrent path: Deluge @ Betty, label `lidarr`, import `/seedbox/music/` |
| **seed-09** | Deploy slskd on Betty |
| **nas-29** | Deploy Soularr on NAS |
| **nas-30** | Optional beets tag layer |
| **docker-16** | Deploy MusicSeerr on Mac mini |
| **seed-06** | Wire MusicSeerr → NAS Lidarr + Plex + Navidrome |
| **seed-10** | E2E music verification (torrent + Soulseek paths) |
| **docker-05** | Navidrome (playback; NFS mount of same library) |

Core TV/movie pipeline (Seerr, seed-05/07) can complete before the music stack.

---

## Deploy MusicSeerr (docker-16)

Prerequisites: `docker-02` (edge network + `/opt/stacks`), `nas-00d` (NFS export of
`/volume1/music`), `nas-23` (Lidarr wired to Deluge).

```bash
# From MacBook — same NFS mount as Navidrome (docker-05)
ssh mini 'sudo mkdir -p /mnt/nas/music && grep -q /mnt/nas/music /etc/fstab || \
  echo "192.168.10.4:/volume1/music /mnt/nas/music nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab'
ssh mini 'sudo mount -a && ls /mnt/nas/music'

scp -r ~/Documents/Home/foss-setup/configs/docker-stack/stacks/musicseerr mini:/tmp/musicseerr
ssh mini 'sudo mkdir -p /opt/stacks/musicseerr && sudo rsync -a /tmp/musicseerr/ /opt/stacks/musicseerr/'
ssh mini 'cd /opt/stacks/musicseerr && cp -n .env.example .env'
ssh mini 'cd /opt/stacks/musicseerr && docker compose up -d'
```

Browse: `http://macmini.<tailnet>:8688` — create admin on first launch.

---

## Wire MusicSeerr (seed-06)

In MusicSeerr → **Settings**:

| Integration | Value |
|-------------|-------|
| **Lidarr** | URL `http://192.168.10.4:8686`, API key from Lidarr → Settings → General |
| **Lidarr root folder** | `/music` (container path on NAS) |
| **Plex** (optional) | NAS server `http://192.168.10.4:32400` + token — availability badges |
| **Navidrome** (optional) | `http://navidrome:4533` (same `edge` network on Mac mini) |
| **Local files** (optional) | Music directory path `/music` (matches compose mount) |

Test: request a small album → appears in **NAS Lidarr Activity** → not on Betty's panel
(Betty only sees Deluge/slskd after Lidarr/Soularr grab).

---

## Deploy slskd on Betty (seed-09)

**Use the native binary** — rootless Docker on Bytesized cannot expose peer port 50300.

```bash
scp ~/Documents/Home/foss-setup/scripts/media/install-slskd-native.sh seedbox:~/
scp ~/Documents/Home/foss-setup/configs/seedbox/slskd-native.example.env seedbox:~/slskd-native/.env
ssh seedbox 'chmod 600 ~/slskd-native/.env && bash ~/install-slskd-native.sh'
```

Edit `~/slskd-native/.env` on Betty for credentials (see below). Create an slskd API key
for Soularr (nas-29). Web UI stays on `127.0.0.1:5030` (SSH tunnel or Tailscale only).

### slskd credentials (`~/slskd-native/.env`)

| Variable | Purpose |
|----------|---------|
| `SLSKD_SLSK_USERNAME` / `SLSKD_SLSK_PASSWORD` | Soulseek network login (slsknet.org account) |
| `SLSKD_WEB_USERNAME` / `SLSKD_WEB_PASSWORD` | Web UI login at http://localhost:5030 |
| `SLSKD_HTTP_IP` | API bind address — `127.0.0.1` for SSH tunnel only; Betty Tailscale IP when Soularr needs API access |
| `SLSKD_API_KEY` | Optional; for Soularr (or create in web UI) |

After editing: `systemctl --user restart slskd`

---

## Deploy Soularr on NAS (nas-29)

See `configs/nas/media-automation/soularr/config.ini.example`.

Soularr `config.ini` keys:

| Section | Key | Value |
|---------|-----|-------|
| Lidarr | `host_url` | `http://lidarr:8686` |
| Lidarr | `download_dir` | `/seedbox/slskd` |
| Slskd | `host_url` | `http://betty.<tailnet>:5030` |
| Slskd | `download_dir` | `/downloads` (inside Betty's slskd container) |

---

## beets tag layer (nas-30, optional)

Lidarr owns layout. beets only writes tags in place:

```bash
cd /volume1/docker/media-automation
cp beets/config.yaml.example beets/config.yaml
docker compose --profile music-tags run --rm beets beet write
```

**Do not** run `beet import` with move/copy — breaks Lidarr naming and iPod sync paths.

---

## Verification (seed-10)

1. **Torrent path:** Request album in MusicSeerr → Lidarr Wanted → Deluge `files/music/`
   → NAS import to `/volume1/music` → Plex Music + Navidrome.
2. **Soulseek path:** Add album in Lidarr Wanted → Soularr searches slskd → `files/slskd/`
   → Lidarr import from `/seedbox/slskd/`.
3. Optional: `beet write` refreshes tags without moving files.

---

## Reference docs

| Topic | URL |
|-------|-----|
| MusicSeerr | https://musicseerr.com/docs/getting-started/ |
| Lidarr | https://wiki.servarr.com/lidarr |
| slskd | https://github.com/slskd/slskd |
| Soularr | https://github.com/mrusse/soularr |
| beets | https://beets.readthedocs.io/ |

---

## Legacy note

`slskd-soularr-compose.example.yaml` (both services on the seedbox) and
`lidarr-slskd-soularr.md` are **deprecated**. Use slskd on Betty + Soularr on NAS.
`music-pipeline-soulseek.md` is a redirect stub — this file is canonical.
