# Plex Media Server on the DS920+ (Synology)

**Phase 2.** Plex runs on the **NAS** (not the Mac mini). Libraries read directly from the
three-volume layout — no sync agent, no second copy step.

| Library | DSM path | Volume |
|---|---|---|
| Movies | `/volume2/movies` | Vol 2 |
| TV Shows | `/volume3/tv` | Vol 3 |
| Music | `/volume1/music` | Vol 1 |
| Books (optional) | `/volume1/books` | Vol 1 |
| YouTube archive (optional) | `/volume1/youtube` | Vol 1 |

The *arr stack (`../media-automation/`) imports into the same paths; Plex picks up new files on
library scan.

---

## 1. Install (Synology Package Center — recommended for Quick Sync)

1. DSM → **Package Center** → search **Plex Media Server** → **Install**.
2. Open the package → **Open** (or browse to `http://<nas-ip>:32400/web`).
3. Sign in with your Plex account (lifetime Plex Pass).
4. **Claim** the server if prompted.

> Container Manager works too, but the native DSM package is simpler on a DS920+ and maps Intel
> Quick Sync cleanly for hardware transcoding.

---

## 2. Add libraries (exact paths)

Settings → **Manage** → **Libraries** → **Add Library**:

1. **Movies** → `/volume2/movies`
2. **TV Shows** → `/volume3/tv`
3. **Music** → `/volume1/music`
4. *(Optional)* **Other Videos** → `/volume1/youtube` (Pinchflat output)

Enable **Scan my library automatically** and **Run a partial scan when changes are detected**.

---

## 3. Hardware transcoding (Quick Sync)

Settings → **Transcoder**:

- **Use hardware acceleration when available** → ON
- **Use hardware-accelerated video encoding** → ON (if shown)
- Transcoder temporary directory: leave default or point at `/volume1/cache/plex` if you create it

Verify: play a file that needs transcoding → Dashboard → **Status** shows `hw` in the transcode line.

---

## 4. Migrating from Ubuntu (Mac mini)

Only after **nas-00d** exports work and media is already on the three-volume paths.

### Recommended: full state migration (preserves users + watch history)

Use this when you want Home users, resume positions, and view counts without
re-inviting everyone or rebuilding from scratch.

1. On Ubuntu: `docker compose stop` in the Plex stack dir. **Do not** run old and new
   Plex simultaneously (same `MachineIdentifier` in `Preferences.xml`).
2. Take a **fresh** copy from Ubuntu appdata (linuxserver layout under
   `configs/plex/Library/Application Support/Plex Media Server/`). Stop Plex before
   copying DB files; omit `-wal`/`-shm` if the server was running.
3. Copy into the DSM Plex data directory (Package Center → Plex → **Installation
   folder**, typically under `/volume1/PlexMediaServer/`):

   | Priority | Copy | Skip |
   |---|---|---|
   | **P0** | `Preferences.xml`, `.LocalAdminToken`, `Plug-in Support/Databases/com.plexapp.plugins.library.db`, `com.plexapp.plugins.library.blobs.db` | |
   | **P1** | `Plug-in Support/Preferences/`, `Plug-in Support/Data/` | |
   | **P2** | `Metadata/`, `Media/` (saves re-downloading art and chapter markers) | |
   | — | | `Logs/`, `Plug-in Support/Caches/`, dated `*.db-2026-*` backups, `*.pid` |

   Recommended total: ~6.7 GB (P0 + P1 + P2).

4. Install Plex from Package Center if not already installed. **Do not** go through
   the first-run claim wizard if `Preferences.xml` already contains a valid
   `PlexOnlineToken`.
5. Add libraries pointing at the DSM paths in §2 (`/volume2/movies`, `/volume3/tv`,
   `/volume1/music`). If the migrated DB already lists `/movies`, `/tv`, `/music`
   as library roots, Plex may match automatically after scan; otherwise run **Scan
   Library Files** on each library.
6. Settings → Transcoder → hardware acceleration ON (Quick Sync).
7. Verify: Home users appear under Settings → Users & Sharing; resume playback
   works on a known in-progress title; HW transcode shows `hw` in Dashboard.
8. Update Mac mini integrations (Overseerr, Tautulli) with the NAS Plex URL/token
   if the server IP changed.
9. Remove the Ubuntu Plex stack once playback is confirmed (seed-08).

### Fallback: fresh libraries (scan only)

If you skip the appdata copy:

1. Stop Ubuntu Plex.
2. Install Package Center Plex on the NAS; sign in and claim.
3. Add libraries at the paths in §2; run **Scan Library Files**.
4. Home users must be re-invited; watch history starts fresh (Plex Pass cloud sync
   may restore some state, but local resume positions are lost).

> A local `migration-snapshot/` on your Mac is useful as a reference but may be
> stale for *arr DBs — always copy from the live Ubuntu host at cutover time.

---

## 5. Backup

Plex config/appdata lives under the package's data directory (typically under
`/volume1/PlexMediaServer` or Package Center → Plex → **Installation folder**). Include that path in
**Hyper Backup** Tier 1 (see `../backup-architecture.md`). Media itself is Tier 2 and is backed up
separately.

---

## 6. Seerr + MusicSeerr + *arr integration

**Seerr** (Mac mini) links to **this** Plex server for movies/TV requests — wired to NAS
Sonarr/Radarr only (seed-05). **MusicSeerr** (Mac mini, `:8688`) is the album request
portal wired to NAS Lidarr (seed-06). Plex Music scans `/volume1/music` when Lidarr
imports land. Betty runs Deluge + slskd (P2P off-site); Soularr on the NAS bridges
Soulseek. See `configs/seedbox/music-pipeline.md`.
