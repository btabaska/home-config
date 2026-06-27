# Home media-automation stack (NAS DS920+) — wiring & operations

**Phase 2.** This folder is the **full home \*arr stack**, running on the
**Synology DS920+** (Container Manager), co-located with the library at
`/volume1/media`. The off-site seedbox **"Betty"** (Bytesized AppBox,
`185.162.184.38`, home `/home/hd34/btabaska`) runs **ONLY Deluge** — it downloads
and seeds, permanently. Nothing else is ever added to the seedbox.

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
 /volume1/media  ──▶ Plex, Rhythmbox/libgpod iPod, Calibre-Web-Automated/Kobo
```

Files in this folder:

| File | Purpose |
|---|---|
| `docker-compose.yml` | the stack (Task 1) |
| `.env.example` | PUID/PGID/TZ + DB password (copy to `.env`) |
| `unpackerr/unpackerr.conf` | archive extraction (Task 3) |

Related scripts (one level up, `../../scripts/media/`): `rclone-seedbox-mount.sh`,
`rclone-seedbox-watchdog.sh`, `rclone-manual-copy.sh`. Remote definition:
`../../configs/seedbox/rclone.conf.example`.

---

## Shared invariants (the self-check at the bottom must verify these)

1. **Identical `/seedbox` mount + `:rslave`** on every download-touching service
   (`sonarr`, `radarr`, `lidarr`, `readarr`, `unpackerr`). Change-one-change-all —
   the compose uses a YAML anchor (`*seedbox-mount`) so they cannot drift.
2. **Identical PUID/PGID** (TODO from `id <user>`), **TZ=America/New_York**,
   **restart: unless-stopped**, **/config on `/volume1/docker/<app>`**.
3. **Exactly ONE scheduled rclone transfer** — `rclone-manual-copy.sh` (manual
   lane). It never overlaps the \*arr label folders. \*arr media arrives via the
   **live mount + import**, never a scheduled copy.
4. **Music = Lidarr only** (acquisition + import/organize). **No beets.**
5. **Readarr → self-hosted rreading-glasses**, output to the **CWA ingest** folder.

---

## RAM-phased rollout checklist (DS920+ ships 4 GB; 20 GB recommended)

Bring services up in order; each phase is safe to stop at. Use
`docker compose up -d <service>` to add a phase.

- [ ] **Prereqs:** `id <user>` → fill `PUID`/`PGID` in `.env`; set `RG_DB_PASSWORD`.
- [ ] **Mount first:** install rclone on DSM; create `rclone.conf` from the
      example; run `rclone-seedbox-mount.sh`; confirm `/volume1/mounts/seedbox-files`
      lists the seedbox `files/` tree. (Nothing imports without this.)
- [ ] **Boot + watchdog:** add the Task Scheduler boot-up task (mount) and the
      every-5-min task (watchdog).
- [ ] **Phase A (core):** `prowlarr flaresolverr sonarr radarr` → add indexers,
      wire Deluge + remote path mapping, root folders `/media/TV`, `/media/Movies`.
- [ ] **Phase B (extend):** `lidarr` + `readarr rreading-glasses rreading-glasses-db`
      → music + books pipelines (below).
- [ ] **Phase C (polish):** `unpackerr` → fill API keys in `unpackerr.conf`.
- [ ] **Manual lane:** add the every-15-min Task Scheduler task for
      `rclone-manual-copy.sh`.
- [ ] Run the **self-check** (bottom of this file).

---

## §3. Download clients — remote Deluge (all \*arrs)

Every \*arr uses the **same remote Deluge** on the seedbox as its download client:

- Settings → Download Clients → **+ Deluge**
- Host `185.162.184.38`, Port = **Deluge daemon port**, Password = **daemon password**
- **Label** per app: `sonarr`, `radarr`, `lidarr`, `readarr` (and `manual` is
  set seedbox-side for the non-\*arr lane). Deluge moves completed downloads into
  the label's folder under `/home/hd34/btabaska/files/<label>`.
- **Remove Completed = OFF** in every \*arr (see §7 — preserves seeding).

---

## §4. Music pipeline — Lidarr only (NO beets, NO slskd/Soularr)

Lidarr does **both** acquisition **and** final import/organize into `/media/Music`.

- **Download client:** remote Deluge, host `185.162.184.38`, daemon port + daemon
  password, **label `lidarr`** → seedbox `/home/hd34/btabaska/files/music`.
- **Remote Path Mapping:** `/home/hd34/btabaska/files/` → `/seedbox/` (§7).
- **Root folder:** `/media/Music`.
- **Metadata/quality profile:** set a profile that is **FLAC-preferred with MP3
  fallback**; pick a consistent **track naming scheme** (Lidarr → Settings → Media
  Management → Track Naming → Rename Tracks ON).
- **Indexer:** music acquisition needs a **music-capable indexer in Prowlarr**
  (torrent trackers are thin for music — add one that actually carries it).

> **Do NOT change the `/media/Music` naming scheme without checking both
> consumers.** `/media/Music` is read by **Plex** AND by the **Rhythmbox/libgpod
> iPod sync**. The library is always kept current; the **iPod's last hop happens
> on physical connect** — it syncs from the master when you plug it in.

---

## §5. Books pipeline — Readarr + self-hosted rreading-glasses → CWA

- **Self-host rreading-glasses** (in this compose) with its **own Postgres**.
  Point **Readarr's metadata provider** at the **local** instance, NOT a public
  one: Readarr → browse to the hidden page `http://<nas>:8787/settings/development`
  → **Metadata Provider Source** = `http://rreading-glasses:8788` → Save.
- **Download client:** remote Deluge, **label `readarr`** → seedbox
  `/home/hd34/btabaska/files/books`. **Remote Path Mapping** `/home/hd34/btabaska/files/`
  → `/seedbox/` (§7).
- **Import target = the CWA INGEST folder.** Readarr's **root folder** is set to
  `/cwa-book-ingest` (mapped to `/volume1/docker/calibre-web-automated/ingest`).
  **Readarr does NOT own the final library** — it drops the imported file into
  CWA's ingest; **CWA converts/organizes into the Calibre library**.
- **Indexer:** book acquisition needs a **book-capable indexer in Prowlarr**.

**Downstream:** CWA → Calibre library → **Kobo via KOReader OPDS** (auto-pull on
WiFi wake). Like the iPod, the **last hop is on the device** — the library stays
current; the Kobo pulls when it wakes on WiFi.

> **Books are inherently less reliable than video.** There is no organized
> "scene" for books, metadata is messier, and the original Readarr project is
> retired (we run the final immutable build + rreading-glasses to revive
> metadata). **Expect occasional manual metadata fixes** — this is normal, not a
> misconfiguration. Maintained community Readarr forks
> (`pennydreadful/bookshelf`, `faustvii/readarr`) are a later migration option.

---

## §6. Non-\*arr / manual downloads lane

For things you grab by hand (not via an \*arr):

- **Seedbox-side:** add a Deluge **`manual`** label → `/home/hd34/btabaska/files/manual`.
- **The ONE scheduled job:** `rclone-manual-copy.sh` runs
  `rclone copy seedbox:/home/hd34/btabaska/files/manual /volume1/media/manual
  --min-age 5m --transfers 4`.
  - **COPY** keeps the file **seeding** and is **re-run-safe** (idempotent).
  - It is scoped **only** to `manual/` — it **never touches the \*arr label
    folders**.
- **Throwaway variant:** for non-seeding public grabs, swap `copy` → `move`
  (`move` deletes the source after transfer, stopping the seed and freeing
  seedbox space). Only for files you do **not** want to seed.

---

## §7. Remote Path Mapping + root folders (set in each UI)

**Remote Path Mapping** — add to **each \*arr that uses Deluge** (Sonarr, Radarr,
Lidarr, Readarr), Settings → Download Clients → Remote Path Mappings:

| Host | Remote Path | Local Path |
|---|---|---|
| `185.162.184.38` | `/home/hd34/btabaska/files/` | `/seedbox/` |

This makes the path Deluge reports resolve to the rclone mount inside the
container. Unpackerr needs **no mapping of its own** — it acts on the
already-mapped path (`/seedbox/...`) and sees `/seedbox` at the identical place.

**Root folders:**

| App | Root folder |
|---|---|
| Sonarr | `/media/TV` |
| Radarr | `/media/Movies` |
| Lidarr | `/media/Music` |
| Readarr | `/cwa-book-ingest` *(CWA ingest — CWA owns the final library; the generic `/media/Books` location is where CWA's organized library is surfaced for Plex)* |

**Download-client settings — leave "Remove Completed" OFF in every \*arr.** This
preserves seeding on the box. **Import is a cross-filesystem COPY, not a
hardlink** (the seedbox SFTP mount and `/volume1/media` are different
filesystems), so the seeding copy stays on the seedbox and a named copy lands in
the library — at the cost of the extra copy (expected; do not try to "fix" it
with hardlinks here).

---

## Final self-check (report violations; don't silently fix)

Run after deploy. Each line is a hard invariant:

1. **Identical `/seedbox` + `:rslave`:**
   `docker inspect sonarr radarr lidarr readarr unpackerr \
   --format '{{.Name}}{{range .Mounts}} {{.Destination}}({{.Propagation}}){{end}}'`
   → every one must show `/seedbox(rslave)`.
2. **One scheduled rclone job, no overlap:** exactly one Task Scheduler entry runs
   `rclone-manual-copy.sh`; its `SRC` ends in `/files/manual`; no scheduled job
   copies `tv|movies|music|books`.
3. **Music = Lidarr only:** no `beets`/`slskd`/`soularr` container or job exists;
   Lidarr root folder `/media/Music`, naming/rename ON.
4. **Readarr metadata + output:** metadata provider = `http://rreading-glasses:8788`
   (local, not a public URL); Readarr root folder = `/cwa-book-ingest`.
5. **Identical PUID/PGID/TZ, restart, /config** across all services.
