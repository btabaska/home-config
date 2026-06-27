> ## ⚠️ SUPERSEDED (2026 architecture change) — read this first
>
> This runbook describes the **old** model (the \*arr suite + qBittorrent running
> **on the seedbox**). The current architecture is different and is **not up for
> re-litigation**:
>
> - **Seedbox "Betty" runs ONLY Deluge** — download + seed, nothing else.
> - **The full \*arr stack runs on the NAS (DS920+)**, reading completed
>   downloads through an **rclone SFTP mount** of the seedbox `files/` folder and
>   reaching Deluge over its **API**.
>
> **Use [`../nas/media-automation/`](../nas/media-automation/) instead** (compose,
> `unpackerr.conf`, README) plus the rclone scripts in `../../scripts/media/`.
> The sections below are kept only as historical reference for the TRaSH
> naming/quality and Prowlarr concepts, which still apply on the NAS.

# *arr Suite Wiring on the Seedbox (Sonarr / Radarr / Prowlarr / qBittorrent / Bazarr)

**Phase 2.** Everything in this runbook runs **on the off-site seedbox**, installed from the
provider's one-click app catalog. The home Mac mini only runs **Seerr** (request portal) and
reaches this stack over Tailscale. Plex (home, on the NAS) imports the finished files after the
sync agent copies them down.

> Order of operations: install apps → set consistent paths → wire qBittorrent → Prowlarr indexers
> → connect Prowlarr to Sonarr/Radarr → quality/naming via TRaSH/Recyclarr → Bazarr → Seerr.

> **Deployment model (no-root managed box).** Bytesized "Stream +3" is a *managed,
> no-root* AppBox. **qBittorrent + Sonarr/Radarr/Prowlarr/Bazarr/Lidarr** install
> from its **one-click catalog** (this runbook). The extras that are NOT in the
> catalog — **slskd, Soularr (`lidarr-slskd-soularr.md`) and Unpackerr
> (`unpackerr-compose.example.yaml`)** — are deployed by you via the **rootless
> Docker** that every Bytesized plan includes (SSH in, `docker compose up -d`, no
> sudo). On a provider that offers neither a one-click nor Docker for those tools,
> you'd need a root-capable/VPS tier instead.

---

## 0. Reference docs (ground every step here)

| Topic | URL |
|---|---|
| Sonarr wiki | https://wiki.servarr.com/sonarr |
| Radarr wiki | https://wiki.servarr.com/radarr |
| Prowlarr wiki | https://wiki.servarr.com/prowlarr |
| Prowlarr → apps (sync) | https://wiki.servarr.com/prowlarr/settings#applications |
| Bazarr docs | https://wiki.bazarr.media/ |
| qBittorrent wiki | https://github.com/qbittorrent/qBittorrent/wiki |
| TRaSH — file organization & hardlinks | https://trash-guides.info/Hardlinks/How-to-setup-for/ |
| TRaSH — Sonarr naming scheme | https://trash-guides.info/Sonarr/Sonarr-recommended-naming-scheme/ |
| TRaSH — Radarr naming scheme | https://trash-guides.info/Radarr/Radarr-recommended-naming-scheme/ |
| TRaSH — Sonarr quality settings | https://trash-guides.info/Sonarr/Sonarr-Quality-Settings-File-Size/ |
| TRaSH — Radarr quality profiles | https://trash-guides.info/Radarr/radarr-setup-quality-profiles/ |
| TRaSH — remote path mapping (Sonarr) | https://trash-guides.info/Sonarr/Tips/Sonarr-remote-path-mapping/ |
| TRaSH — remote path mapping (Radarr) | https://trash-guides.info/Radarr/Tips/Radarr-remote-path-mapping/ |
| Recyclarr (auto-sync TRaSH) | https://recyclarr.dev/guide/getting-started/ |

---

## 1. Paths: one root tree so hardlinks/atomic moves work

This is the single most important decision and the #1 cause of "stuck in queue / copies instead of
moves" problems. **All apps must see the same filesystem under one root.** On a managed seedbox your
home directory is that root (e.g. `/home/<user>`). Lay it out like TRaSH's `/data` pattern:

```
/home/<user>/data/
├── torrents/
│   ├── movies/        # qBittorrent category "radarr" saves here
│   └── tv/            # qBittorrent category "sonarr" saves here
└── media/
    ├── movies/        # Radarr root folder  +  what the sync agent pulls to the NAS
    └── tv/            # Sonarr root folder   +  what the sync agent pulls to the NAS
```

Because `torrents/` and `media/` are on the **same filesystem**, Radarr/Sonarr hardlink on import:
the file stays seeding in `torrents/` AND appears named in `media/` using zero extra space. Ref:
https://trash-guides.info/Hardlinks/How-to-setup-for/

> If the provider gives separate mounts for "downloads" vs "data", you lose hardlinks (it falls back
> to copy+delete, doubling disk use). Pick a plan/layout that keeps them on one volume.

---

## 2. qBittorrent

1. Open the WebUI (provider gives the URL; change the default password immediately).
2. **Tools → Options → Downloads**:
   - Default Save Path: `/home/<user>/data/torrents`
   - Keep incomplete torrents in a separate `.../torrents/incomplete` (optional) but keep it on the
     same volume.
   - Enable **"Automatically add torrents from"** is NOT needed — the *arr apps push torrents in.
3. **Categories** (right-click the Categories pane → Add category) — these map 1:1 to the *arr download client config:
   - `radarr`  → save path `/home/<user>/data/torrents/movies`
   - `sonarr`  → save path `/home/<user>/data/torrents/tv`
4. **Connection / privacy**: a seedbox already gives you a clean datacenter IP, so no VPN is needed
   on the box. For private trackers, leave encryption at "Allow" unless the tracker requires
   otherwise, and do **not** cap upload (you want ratio — that's the whole point of unlimited upload).
5. Note the WebUI host/port + username/password — Sonarr/Radarr need them next.

---

## 3. Sonarr & Radarr — root folders + download client

Do this in **both** Sonarr (TV) and Radarr (movies); they're identical except paths/ports.

### 3a. Root folder
- Sonarr → Settings → Media Management → Root Folders → Add: `/home/<user>/data/media/tv`
- Radarr → Settings → Media Management → Root Folders → Add: `/home/<user>/data/media/movies`

### 3b. Download client (qBittorrent)
Settings → Download Clients → **+** → qBittorrent:
- Host: `localhost` (everything is on the same seedbox)
- Port: qBittorrent WebUI port
- Username / Password: from step 2.5
- Category: `sonarr` (in Sonarr) / `radarr` (in Radarr)
- Test → Save.

### 3c. Remote path mapping — NOT needed here
Because Sonarr/Radarr **and** qBittorrent run on the same seedbox with one path tree, the path
qBittorrent reports is the path the *arr app sees. **Leave Remote Path Mappings empty.** Only add a
mapping if you deliberately split paths across mounts (discouraged). Ref:
https://trash-guides.info/Sonarr/Tips/Sonarr-remote-path-mapping/

### 3d. Completed Download Handling
Settings → Download Clients → enable "Completed Download Handling" (default on). On import the app
hardlinks from `torrents/` into `media/`, renames per the scheme below, and the original keeps seeding.

---

## 4. Prowlarr — add indexers once, sync to everything

1. Prowlarr → **Indexers → Add Indexer**: add your private/public trackers (and any Usenet indexers).
   Use the in-app search to test each one returns results.
2. Prowlarr → **Settings → Apps → Add Application**:
   - **Sonarr**: Sync Level = **Full Sync**; Prowlarr Server `http://localhost:9696`;
     Sonarr Server `http://localhost:8989`; API Key from Sonarr → Settings → General.
   - **Radarr**: Sync Level = **Full Sync**; Radarr Server `http://localhost:7878`;
     API Key from Radarr → Settings → General.
3. Save. Prowlarr pushes every indexer into Sonarr/Radarr automatically and keeps them in sync.
   Force a sync any time with:
   ```bash
   curl -X POST "http://localhost:9696/api/v1/applications/sync" -H "X-Api-Key: <PROWLARR_API_KEY>"
   ```
   Ref: https://wiki.servarr.com/prowlarr/settings#applications

> After this, do NOT add indexers directly in Sonarr/Radarr — manage them only in Prowlarr.

---

## 5. Quality profiles + naming — TRaSH Guides (via Recyclarr)

Doing this by hand is hundreds of custom-format clicks. Use **Recyclarr** to pull TRaSH's profiles,
custom-format scores, quality definitions, AND naming into Sonarr/Radarr, then re-run it to stay current.

1. Install Recyclarr on the seedbox (most catalogs offer it; else the binary/Docker image).
   Getting started: https://recyclarr.dev/guide/getting-started/
2. List + create from a template, then edit `base_url`/`api_key`:
   ```bash
   recyclarr config list templates
   recyclarr config create --template radarr-hd-bluray-web   # example
   ```
3. Add a `media_naming` block so naming is managed too (folder + file). Example for Radarr:
   ```yaml
   radarr:
     main:
       base_url: http://localhost:7878
       api_key: <RADARR_API_KEY>
       quality_definition:
         type: movie
       quality_profiles:
         - trash_id: d1d67249d3890e49bc12e275d989a7e9   # "HD Bluray + WEB"
           reset_unmatched_scores:
             enabled: true
       media_naming:
         folder: plex-tmdb
         movie:
           rename: true
           standard: plex-tmdb
   ```
4. Apply:
   ```bash
   recyclarr sync
   ```
5. Pick a profile that matches your use:
   - Quality over size → **Remux + WEB 1080p** (or 2160p for 4K)
   - Balanced → **HD Bluray + WEB**
   - Space-conscious → **WEB 1080p**

### If you set naming by hand instead
Settings → Media Management → enable **Rename Episodes/Movies** and paste TRaSH's recommended scheme.

Sonarr standard episode format (https://trash-guides.info/Sonarr/Sonarr-recommended-naming-scheme/):
```
{Series CleanTitleWithoutYear} {(Series Year)} - S{season:00}E{episode:00} - {Episode CleanTitle:90} {[Custom Formats]}{[Quality Full]}{[Mediainfo AudioCodec}{ Mediainfo AudioChannels]}{[MediaInfo VideoDynamicRangeType]}{[Mediainfo VideoCodec]}{-Release Group}
```
Radarr movie naming follows https://trash-guides.info/Radarr/Radarr-recommended-naming-scheme/ —
use the `plex` / `plex-tmdb` folder + file templates so Plex matches cleanly on the NAS.

> Why naming matters: complete, consistent names prevent re-download loops on import and let Plex
> (home) match every title. The names produced here are exactly what the sync agent copies to the NAS.

---

## 6. Bazarr — subtitles

1. Bazarr → **Settings → Sonarr** and **Settings → Radarr**: point each at `http://localhost:8989`
   / `http://localhost:7878` with their API keys so Bazarr sees the same library.
2. **Settings → Languages**: create a languages profile (e.g. English) and assign it as default for
   series and movies.
3. **Settings → Providers**: enable subtitle providers (OpenSubtitles account, etc.).
4. Bazarr writes sidecar `.srt` files **next to the media** in `data/media/...`, so they ride along
   when the sync agent pulls the folder to the NAS. Ref: https://wiki.bazarr.media/

---

## 7. Connect Seerr (home Mac mini) to the seedbox *arr apps

Seerr runs at home; it must reach Sonarr/Radarr on the seedbox **over Tailscale** (see
`verify-tailscale-seedbox.sh` and Section 8 of the plan).

In Seerr → Settings → Services:
- **Add Radarr**: Hostname = seedbox Tailscale name/IP (e.g. `seedbox.<tailnet>.ts.net`),
  Port `7878`, API key from Radarr, default root folder `/home/<user>/data/media/movies`, default
  quality profile = the TRaSH profile from Section 5.
- **Add Sonarr**: same idea, port `8989`, root `/home/<user>/data/media/tv`.
- Test → Save. Now a household request flows: Seerr → Sonarr/Radarr (seedbox) → Prowlarr search →
  qBittorrent → import/rename → Bazarr subs → sync agent → Plex → Seerr marks "Available."

> Nothing here is port-forwarded. All home↔seedbox traffic is on the tailnet.

---

## 8. Verify the pipeline end-to-end

1. In Seerr, request one small known title.
2. Watch it appear in Radarr/Sonarr → grabbed in qBittorrent → imported (hardlinked) into
   `data/media/...` with the TRaSH name.
3. Confirm a subtitle `.srt` lands beside it (Bazarr).
4. Run the sync agent (`seedbox-sync.sh`) and confirm the named file + subs arrive in the NAS library.
5. Plex scans, the title shows up, Seerr flips to "Available" and notifies the requester.
