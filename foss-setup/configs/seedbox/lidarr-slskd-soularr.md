# Lidarr + slskd + Soularr — music acquisition on the seedbox

**Phase 2.** Music slots into the *same* off-site seedbox pipeline as movies/TV
(see `arr-suite-wiring.md`), with one twist: **torrent trackers are thin for
music**, so we bolt on **Soulseek** — the long-running P2P network where the
actual music lives — via a self-hosted daemon (**slskd**) glued to **Lidarr** by
**Soularr**. Everything here runs **on the seedbox** (Soulseek is P2P; it needs to
be where the data tree and the *arrs are). Finished albums get pulled to the NAS
music library by the sync agent and served at home by **Navidrome**.

> Pipeline at a glance:
> Lidarr (wanted) → Soularr → slskd (Soulseek search/download) → Lidarr import →
> `data/media/music` → `seedbox-sync.sh` → NAS music library → Navidrome.

---

## 0. Reference docs

| Topic | URL |
|---|---|
| Lidarr wiki | https://wiki.servarr.com/lidarr |
| slskd | https://github.com/slskd/slskd |
| slskd config reference | https://github.com/slskd/slskd/blob/master/docs/config.md |
| Soularr | https://github.com/mrusse/soularr |
| TRaSH hardlinks / folder layout | https://trash-guides.info/Hardlinks/How-to-setup-for/ |

---

## 1. Why a second download path (Soulseek), not just torrents

Private/public **torrent** trackers cover movies and TV well but are **sparse for
music** — many albums, editions, and discographies simply aren't seeded. The
**Soulseek** network is where music actually lives (lossless + lossy, deep
back-catalogue). It's **P2P**, so we run a daemon (**slskd**) directly on the
seedbox and let **Soularr** automate it against Lidarr's wishlist. Torrents still
work for music where available; Soulseek fills the (large) gaps.

---

## 2. Paths — extend the one-root tree with `music`

Reuse the single data tree from `arr-suite-wiring.md` §1 (so hardlinks/atomic
moves work) and add music alongside movies/tv:

```
/home/<user>/data/
├── torrents/
│   ├── movies/        # qBittorrent category "radarr"
│   ├── tv/            # qBittorrent category "sonarr"
│   └── music/         # qBittorrent category "lidarr" (torrent music, when available)
├── downloads/
│   └── slskd/         # slskd writes Soulseek downloads here (shared with Soularr)
└── media/
    ├── movies/
    ├── tv/
    └── music/         # Lidarr root folder + what the sync agent pulls to the NAS
```

`seedbox-sync.sh` already pulls `data/media/{movies,tv}` to the NAS; add a music
pair so it also pulls `data/media/music` → the NAS music library. For example,
override its env in the crontab line:

```bash
REMOTE_MOVIES=data/media/music LOCAL_MOVIES=/volume1/media/music /…/seedbox-sync.sh
```

(or add a third `pull` pair to your copy of the script). The NAS music library is
what **Navidrome** indexes and streams to Symfonium/Amperfy.

---

## 3. Deploy slskd + Soularr (on the seedbox)

Use the compose template `slskd-soularr-compose.example.yaml` in this folder:

```bash
cp configs/seedbox/slskd-soularr-compose.example.yaml docker-compose.yml
cp .env.example .env          # set Soulseek creds, slskd web creds, MUSIC_DOWNLOADS
docker compose up -d
```

Key points (all enforced by the template):
- **slskd** exposes its web UI/API on `:5030` and the Soulseek listen port `:50300`.
- **slskd** and **Soularr** share **one** `/downloads` volume so Soularr/Lidarr can
  see exactly what slskd downloaded. Point `MUSIC_DOWNLOADS` at
  `/home/<user>/data/downloads/slskd`.
- A free **Soulseek account** is required (`SLSKD_SLSK_USERNAME`/`PASSWORD`).
- Soularr's `config.ini` (mounted at `/data`) holds the **Lidarr URL + API key**
  and the **slskd URL + API key**; set `SCRIPT_INTERVAL` for how often it runs.

---

## 4. Wire Lidarr

1. **Root folder** — Lidarr → Settings → Media Management → Root Folders → Add:
   `/home/<user>/data/media/music` (matches the tree in §2 so imports hardlink).
2. **Quality/metadata profiles** — pick a quality profile (e.g. Lossless preferred,
   MP3-320 fallback) and a metadata profile, so Lidarr knows what to want.
3. **Indexers (torrents)** — Prowlarr already syncs indexers to Lidarr
   (`arr-suite-wiring.md` §4); add Lidarr as an application in Prowlarr so any
   music torrent indexers flow in. This is the torrent half.
4. **Download client (torrents)** — add qBittorrent in Lidarr with category
   `lidarr` → save path `/home/<user>/data/torrents/music` (same pattern as
   Sonarr/Radarr).
5. **Soulseek half via Soularr** — you do **not** add slskd as a normal Lidarr
   download client. Instead **Soularr** is the bridge: it reads Lidarr's **Wanted**
   (Missing/Cutoff Unmet) list, searches **slskd**, downloads matches into the
   shared `/downloads`, then tells Lidarr to import them from there. Configure the
   Lidarr + slskd endpoints and API keys in Soularr's `config.ini`.

> Get the Lidarr API key from Lidarr → Settings → General. Get the slskd API key
> from the slskd web UI (Options → enable an API key) or its config file.

---

## 5. The full flow + verification

1. In Lidarr, add an artist/album so it shows up under **Wanted**.
2. Within `SCRIPT_INTERVAL`, **Soularr** searches **slskd** for the wanted album,
   downloads the best match into `data/downloads/slskd`, and triggers Lidarr.
3. **Lidarr imports** from the download dir into `data/media/music/<Artist>/<Album>`
   with proper naming/tags (hardlink because it's the same filesystem).
4. **`seedbox-sync.sh`** (run on the NAS) copies `data/media/music` down to the NAS
   music library (`/volume1/media/music`).
5. **Navidrome** scans the NAS library and the album is streamable at home.

Cross-references: `slskd-soularr-compose.example.yaml` (the stack), `arr-suite-wiring.md`
(the shared seedbox pipeline + paths), and `../../scripts/media/seedbox-sync.sh`
(the NAS puller — add the music path pair).
