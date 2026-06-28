# Music pipeline — split Soulseek architecture (slskd on seedbox, Soularr + beets on NAS)
#
# Betty runs Deluge (torrents) + **slskd** (Soulseek P2P). The NAS runs Lidarr,
# **Soularr** (Lidarr ↔ remote slskd bridge), and optional **beets** (tag-only).
#
# See:
#   - configs/nas/media-automation/README.md §4
#   - configs/seedbox/slskd-compose.example.yaml
#   - configs/nas/media-automation/soularr/config.ini.example

## Pipeline at a glance

```
Seerr request → Lidarr (NAS) "Wanted"
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  Torrent indexers          Soularr (NAS)
  → Deluge (Betty)          → slskd API (Betty, Tailscale)
  → files/music/            → files/slskd/
        │                       │
        └───────────┬───────────┘
                    ▼
        rclone mount /seedbox/…  (NAS)
                    ▼
        Lidarr import → /volume1/music
                    ▼
        beets write (optional, tag-only)
                    ▼
        Plex · Navidrome · iPod sync
```

---

## 0. Reference docs

| Topic | URL |
|---|---|
| Lidarr wiki | https://wiki.servarr.com/lidarr |
| slskd | https://github.com/slskd/slskd |
| Soularr | https://github.com/mrusse/soularr |
| beets | https://beets.readthedocs.io/ |

---

## 1. Why Soulseek (and why slskd stays on Betty)

Torrent indexers cover music poorly. **Soulseek** fills the gap. It is **P2P**, so the
daemon runs on **Betty** — same rationale as Deluge for torrents. **Soularr** and
**Lidarr** stay on the NAS where the library lives.

---

## 2. Paths

On Betty (host):

```
~/files/
├── tv/           # Deluge label sonarr
├── movies/       # Deluge label radarr
├── music/        # Deluge label lidarr (torrent music)
├── slskd/        # slskd Soulseek downloads  ← NEW
├── books/        # Deluge label readarr
└── manual/       # Deluge label manual
```

On the NAS (inside Lidarr / Soularr containers):

| Host path | Container path | Purpose |
|---|---|---|
| `/volume1/mounts/seedbox-files` | `/seedbox` | rclone SFTP mount of `~/files/` |
| `/volume1/mounts/seedbox-files/slskd` | `/seedbox/slskd` | Soulseek downloads for Lidarr import |
| `/volume1/music` | `/music` | Final library (Plex, Navidrome, iPod) |

**No scheduled copy** — same live-mount + import model as TV/movies. `seedbox-sync.sh`
is legacy only.

---

## 3. Deploy slskd on Betty (seed-09)

```bash
ssh seedbox
mkdir -p ~/files/slskd ~/slskd-stack
cd ~/slskd-stack
cp ~/path/to/foss-setup/configs/seedbox/slskd-compose.example.yaml docker-compose.yml
cp ~/path/to/foss-setup/configs/seedbox/.env.example .env
# Edit .env: SLSKD_SLSK_* creds, SLSKD_DOWNLOADS=/home/hd34/btabaska/files/slskd
docker compose up -d
```

- Register a free Soulseek account (in the app or at slsknet.org).
- Create an slskd API key in the web UI (Options → API) for Soularr.
- Confirm `~/files/slskd` receives a test download.
- **Firewall:** allow Betty `:50300/tcp` for Soulseek peers. Keep `:5030` on tailnet only.

---

## 4. Deploy Soularr on NAS (nas-29)

Soularr is in `media-automation/docker-compose.yml`. After Lidarr (nas-23) and slskd
(seed-09):

```bash
cd /volume1/docker/media-automation
cp soularr/config.ini.example soularr/config.ini
# Edit: Lidarr API key, slskd API key, host_url = http://betty.<tailnet>:5030
docker compose up -d soularr
```

Soularr `config.ini` keys:

| Section | Key | Value |
|---|---|---|
| Lidarr | `host_url` | `http://lidarr:8686` |
| Lidarr | `download_dir` | `/seedbox/slskd` |
| Slskd | `host_url` | `http://betty.<tailnet>:5030` |
| Slskd | `download_dir` | `/downloads` (inside Betty's slskd container) |

---

## 5. Wire Lidarr (torrent + Soulseek)

**Torrent half** (nas-23): remote Deluge, label `lidarr`, imports from `/seedbox/music/`.

**Soulseek half** (Soularr): no slskd download client in Lidarr. Soularr reads
**Wanted**, searches slskd, downloads to `files/slskd/`, triggers Lidarr import from
`/seedbox/slskd/`.

---

## 6. beets tag layer (nas-30, optional)

Lidarr owns layout. beets only writes tags in place:

```bash
cd /volume1/docker/media-automation
cp beets/config.yaml.example beets/config.yaml
docker compose run --rm beets beet write
```

Schedule weekly via DSM Task Scheduler. **Do not** run `beet import` with move/copy —
that fights Lidarr's naming and breaks iPod sync paths.

---

## 7. Verification

1. Add an album in Lidarr → appears under **Wanted**.
2. Within `SCRIPT_INTERVAL`, Soularr searches slskd and downloads to `files/slskd/`.
3. Lidarr imports into `/music` with rename ON.
4. Album appears in Plex Music and Navidrome.
5. Optional: `beet write` refreshes tags without moving files.

---

## Legacy note

`slskd-soularr-compose.example.yaml` (both services on the seedbox) is **deprecated**
for this architecture. Use `slskd-compose.example.yaml` on Betty + Soularr on the NAS.
