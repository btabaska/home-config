# Home media-automation stack (NAS DS920+) — wiring & operations

**Phase 2.** This folder is the **full home \*arr stack**, running on the
**Synology DS920+** (Container Manager), with libraries on **three Basic volumes**
(Vol 1 Music/Books/Docker/Tier 1, Vol 2 Movies, Vol 3 TV). The off-site seedbox
**"Betty"** (Bytesized AppBox, `185.162.184.38`, home `/home/hd34/btabaska`)
runs **ONLY Deluge** — it downloads and seeds, permanently. Nothing else is ever
added to the seedbox.

```
Home apps (NAS)                                   Seedbox "Betty" (off-site)
┌───────────────────────────────┐                ┌──────────────────────────┐
│ sonarr radarr lidarr readarr  │ ── Deluge API ▶│ Deluge  (download + seed)│
│ prowlarr flaresolverr         │                │ files/ tv movies music   │
│ unpackerr                     │ ◀ rclone SFTP ─ │       books manual       │
│ rreading-glasses + postgres   │   mount (read)  └──────────────────────────┘
└───────────────────────────────┘
        │ import (cross-fs copy)
        ▼
 /volume3/tv  /volume2/movies  /volume1/music  ──▶ Plex (3 library roots)
 /volume1/books (via CWA)  ──▶ Kobo; /volume1/music ──▶ Rhythmbox/libgpod iPod
```

Files in this folder:

| File | Purpose |
|---|---|
| `docker-compose.yml` | the stack (Task 1) |
| `.env.example` | PUID/PGID/TZ + NAS path vars + DB password (copy to `.env`) |
| `unpackerr/unpackerr.conf` | archive extraction (Task 3) |
| `migration-from-ubuntu.md` | cutover checklist when importing *arr configs from Ubuntu |

Related scripts: copy `../../scripts/media/rclone-*.sh` to
`/volume1/scripts/media/` on the NAS. Remote definition:
`../../configs/seedbox/rclone.conf.example`.

---

## Shared invariants (the self-check at the bottom must verify these)

1. **Identical `/seedbox` mount + `:rslave`** on every download-touching service
   (`sonarr`, `radarr`, `lidarr`, `readarr`, `unpackerr`). Change-one-change-all —
   the compose uses a YAML anchor (`*seedbox-mount`) so they cannot drift.
2. **Identical PUID/PGID** (TODO from `id <user>`), **TZ=America/New_York**,
   **restart: unless-stopped**, **/config on `${DOCKER_ROOT}/<app>`** (default
   `/volume1/docker/<app>`).
3. **Per-service library mounts only** — sonarr sees `/tv` only, radarr `/movies`
   only, lidarr `/music` only (not a shared `/media` tree).
4. **Exactly ONE scheduled rclone transfer** — `rclone-manual-copy.sh` (manual
   lane → `/volume1/manual`). \*arr media arrives via **live mount + import**.
5. **Music = Lidarr only** (acquisition + import/organize). **No beets.**
6. **Readarr → self-hosted rreading-glasses**, output to the **CWA ingest** folder.

---

## RAM-phased rollout checklist (DS920+ ships 4 GB; 20 GB recommended)

- [ ] **Prereqs:** `id <user>` → fill `PUID`/`PGID` and all path vars in `.env`.
- [ ] **Mount first:** rclone.conf; run `rclone-seedbox-mount.sh`; confirm
      `/volume1/mounts/seedbox-files` lists the seedbox `files/` tree.
- [ ] **Boot + watchdog:** Task Scheduler boot-up = mount; every 5 min = watchdog.
- [ ] **Phase A:** `prowlarr flaresolverr sonarr radarr` → Deluge + mapping;
      root folders `/tv`, `/movies`.
- [ ] **Phase B:** `lidarr` + `readarr rreading-glasses rreading-glasses-db`.
- [ ] **Phase C:** `unpackerr` → fill API keys in `unpackerr.conf`.
- [ ] **Manual lane:** every-15-min Task Scheduler = `rclone-manual-copy.sh`.
- [ ] Run the **self-check** (bottom of this file).

---

## Migrating from Ubuntu (Mac mini)

If you already run Sonarr/Radarr/Lidarr/Readarr on the Ubuntu Docker host, copy
their config dirs into `/volume1/docker/<app>/` **before** first container start,
then rewire indexers and download clients after boot. Full checklist:
**`migration-from-ubuntu.md`**.

Summary of post-import fixes (nas-22):

- Root folders: `/data/tv/` → `/tv`, `/data/movies/` → `/movies`, etc.
- Download client: remove qBittorrent → add remote Deluge on seedbox.
- Indexers: remove Jackett → Prowlarr Full Sync; re-add private indexers from old
  Jackett JSON as a credential reference.

---

## §3. Download clients — remote Deluge (all \*arrs)

Every \*arr uses the **same remote Deluge** on the seedbox:

- Settings → Download Clients → **+ Deluge**
- Host `185.162.184.38`, Port = daemon port, Password = daemon password
- **Label** per app: `sonarr`, `radarr`, `lidarr`, `readarr`
- **Remove Completed = OFF** in every \*arr (preserves seeding).

---

## §4. Music pipeline — Lidarr only (NO beets, NO slskd/Soularr)

Lidarr imports into **`/music`** (host: `/volume1/music`).

- **Download client:** remote Deluge, label `lidarr`.
- **Remote Path Mapping:** `/home/hd34/btabaska/files/` → `/seedbox/`.
- **Root folder:** `/music`.
- **FLAC-preferred with MP3 fallback**; Rename Tracks ON.
- **Music-capable indexer** in Prowlarr.

> Do NOT change `/music` naming without checking **both** Plex and Rhythmbox/libgpod
> iPod sync (`/volume1/music` on the host).

---

## §5. Books pipeline — Readarr + rreading-glasses → CWA

- **Metadata:** Readarr → `http://<nas>:8787/settings/development` → Provider =
  `http://rreading-glasses:8788`.
- **Download client:** Deluge, label `readarr`; mapping as in §7.
- **Root folder:** `/cwa-book-ingest` (host: `${CWA_INGEST}`).
- CWA organizes into **`/volume1/books`** for Plex/Kobo.

---

## §6. Non-\*arr / manual downloads lane

- Deluge **`manual`** label → `files/manual` on Betty.
- **ONE scheduled job:** `rclone-manual-copy.sh` → `/volume1/manual` (COPY, scoped
  to `manual/` only).

---

## §7. Remote Path Mapping + root folders (set in each UI)

| Host | Remote Path | Local Path |
|---|---|---|
| `185.162.184.38` | `/home/hd34/btabaska/files/` | `/seedbox/` |

**Root folders:**

| App | Container root | Host path (default) |
|---|---|---|
| Sonarr | `/tv` | `/volume3/tv` |
| Radarr | `/movies` | `/volume2/movies` |
| Lidarr | `/music` | `/volume1/music` |
| Readarr | `/cwa-book-ingest` | `/volume1/docker/calibre-web-automated/ingest` |

**Plex** needs **separate library roots** for TV, Movies, Music, and Books.

Import is a **cross-filesystem COPY** (seedbox mount vs local volume), not a
hardlink. Leave Remove Completed OFF.

---

## Final self-check (report violations; don't silently fix)

1. **`/seedbox(rslave)`** on sonarr, radarr, lidarr, readarr, unpackerr.
2. **Per-volume library mounts:** sonarr → `/tv` only; radarr → `/movies` only;
   lidarr → `/music` only.
3. **One scheduled rclone job:** manual lane → `/volume1/manual` only.
4. **Lidarr** root `/music`, rename ON; no beets/slskd/soularr.
5. **Readarr** metadata = `http://rreading-glasses:8788`; root `/cwa-book-ingest`.
6. **PUID/PGID/TZ** identical; `/config` under `/volume1/docker/<app>`.

```bash
docker inspect sonarr radarr lidarr readarr unpackerr \
  --format '{{.Name}}{{range .Mounts}} {{.Destination}}({{.Propagation}}){{end}}'
```
