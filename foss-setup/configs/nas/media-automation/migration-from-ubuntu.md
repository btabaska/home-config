# Migrating *arr configs from Ubuntu (Mac mini) to NAS

**Phase 2 cutover.** Use this when moving Sonarr, Radarr, Lidarr, and Readarr from the
Ubuntu Docker host (`/home/btabaska/server/configs/<app>/`) to the NAS stack in this
folder. Overseerr stays on the Mac mini — no action needed there.

> Take a **fresh copy from the live Ubuntu server** at cutover time (containers
> stopped first). A local `migration-snapshot/` on your Mac is a reference only;
> the *arr DBs in that copy may be months stale.

---

## What to copy (per app)

Copy the entire config directory for each app **before** the container's first start
on the NAS:

| Ubuntu source | NAS destination | Key files |
|---|---|---|
| `configs/sonarr/` | `/volume1/docker/sonarr/config/` | `sonarr.db`, `config.xml`, `asp/` |
| `configs/radarr/` | `/volume1/docker/radarr/config/` | `radarr.db`, `config.xml`, `asp/` |
| `configs/liadarr/` *(typo on old host)* | `/volume1/docker/lidarr/config/` | `lidarr.db`, `config.xml`, `asp/` |
| `configs/readarr/` | `/volume1/docker/readarr/config/` | `readarr.db`, `config.xml`, `asp/` |

Skip `logs/`, `Sentry/`, and `*.pid`. The SQLite `.db` files hold the library,
quality profiles, naming, tags, and history.

---

## Copy procedure

1. On Ubuntu: `docker compose stop` for sonarr, radarr, lidarr, readarr.
2. From MacBook: `scp -r mini:/home/btabaska/server/configs/sonarr nas:/tmp/`
   (repeat for radarr, liadarr → `/volume1/docker/lidarr/`, readarr).
3. Move into per-app `/config` mounts: `/volume1/docker/<app>/config/` (LinuxServer
   bind-mount target — **not** the parent `/volume1/docker/<app>/`).
4. Deploy the NAS compose (see README RAM-phased checklist) — configs are pre-seeded.
5. Complete **nas-22** rewire steps below before relying on searches/imports.

---

## Post-import rewire (nas-22)

The old Ubuntu stack used **Jackett + qBittorrent**. The NAS stack uses **Prowlarr +
remote Deluge on the seedbox**. Imported DBs boot cleanly but need these UI fixes:

### 1. Root folders

| App | Old path (Ubuntu) | New path (NAS container) |
|---|---|---|
| Sonarr | `/data/tv/` | `/tv` |
| Radarr | `/data/movies/` | `/movies` |
| Lidarr | `/data/music/` | `/music` |
| Readarr | `/data/books/` | `/cwa-book-ingest` |

After changing, run **Refresh & Scan** so existing files on the NAS volumes re-link.

### 2. Download clients

- **Remove** all qBittorrent entries.
- **Add** remote Deluge @ `185.162.184.38` with label per app (`sonarr`, `radarr`,
  `lidarr`, `readarr`). Remove Completed = OFF.
- Remote Path Mapping: `/home/hd34/btabaska/files/` → `/seedbox/` (see README §7).

### 3. Indexers

- **Remove** all Jackett Torznab indexers (typically `192.168.1.2:9117`).
- In **Prowlarr**: add indexers, then Settings → Apps → Full Sync to each *arr.
- Use old Jackett `Indexers/*.json` files (from your migration snapshot) as a
  **credential reference** when re-adding private indexers (MAM, IPT, 1337x, etc.).
  Do **not** deploy Jackett on the NAS.

### 4. Verify

- Monitored series/movies/artists/books counts match expectations.
- Manual Deluge grab with label `sonarr` imports from `/seedbox` to `/volume3/tv`.
- Run the self-check at the bottom of `README.md`.

---

## Optional: Bazarr

The old Ubuntu stack may include Bazarr (`configs/bazarr/`). This NAS compose does
**not** include Bazarr today. Preserve the snapshot if you add Bazarr later.
