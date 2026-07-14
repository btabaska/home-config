# Home media-automation stack (NAS DS920+) — wiring & operations

> The current home *arr architecture: the full download/import stack runs on the Synology DS920+ (Container Manager), pulling from an off-site seedbox ("Betty") that runs only Deluge. This superseded the old on-seedbox *arr layout.

_Source: `foss-setup/configs/nas/media-automation/README.md` · migrated + validated 2026-07-14_

**Phase 2.** This is the **full home \*arr stack**, running on the **Synology DS920+** (Container Manager), with libraries on **three Basic volumes** (Vol 1 Music/Books/Docker/Tier 1, Vol 2 Movies, Vol 3 TV). The off-site seedbox **"Betty"** (Bytesized AppBox, `185.162.184.38`, home `/home/hd34/btabaska`) runs **ONLY Deluge** — it downloads and seeds, permanently. Nothing else is ever added to the seedbox.

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

!!! note "Validated against live nas (2026-07-14)"
    `docker ps` on the NAS confirms the stack is up (3 days): `sonarr` (`lscr.io/linuxserver/sonarr:4.0.19`), `radarr` (`lscr.io/linuxserver/radarr:6.2.1`), `lidarr` (`lscr.io/linuxserver/lidarr:3.1.0`), `readarr` (`linuxserver/readarr:develop-0.4.18.2805-ls157`), `prowlarr` (`lscr.io/linuxserver/prowlarr:2.4.0`), `flaresolverr` (`ghcr.io/flaresolverr/flaresolverr:v3.5.0`), `unpackerr` (`golift/unpackerr:0.15.2`), `rreading-glasses` (`blampe/rreading-glasses`), `rreading-glasses-db` (`postgres:17.6`, healthy), `soularr` (`ghcr.io/mrusse/soularr:1.2.2`), `beets` (`lscr.io/linuxserver/beets:2.1.0`), `calibre-web-automated` (`ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7`, healthy). Plex is a Synology **package**, not a container. slskd is **native on Betty**, not on the NAS.

## Files in this folder

| File | Purpose |
|---|---|
| `docker-compose.yml` | the stack (Task 1) |
| `.env.example` | PUID/PGID/TZ + NAS path vars + DB password (copy to `.env`) |
| `unpackerr/unpackerr.conf` | archive extraction (Task 3) |
| `migration-from-ubuntu.md` | cutover checklist when importing *arr configs from Ubuntu |

Related scripts: copy `configs/nas/scripts/media/rclone-*.sh` to `/volume1/scripts/media/` on the NAS. Remote definition: `foss-setup/configs/seedbox/rclone.conf.example`. (Repo source dir: `foss-setup/configs/nas/media-automation/`.)

---

## §0. Seedbox mount — reliability design (nas-20 backbone)

The rclone SFTP mount is the **single point of failure** for the entire media pipeline. A dropped mount silently stalls all \*arr imports with no error.

### How it works

```
DSM boot → rclone-seedbox-mount.sh (boot trigger, root)
              └─ launches rclone daemon (--daemon)
              └─ waits for FUSE handle in /proc/self/mountinfo (no SFTP ls)
              └─ restarts *arr containers so plain bind sees the new mount

Every 5 min → rclone-seedbox-watchdog.sh (scheduled, root)
              └─ if not in mountinfo     → remount immediately
              └─ if ls times out (once)  → log "suspect", hold off (SFTP lag)
              └─ if ls times out (twice) → confirmed stale → tear down + remount
              └─ on healthy ls          → write /var/run/seedbox-mount.ok
```

!!! note "Validated against live nas (2026-07-14)"
    Mount is present and healthy: `/proc/mounts` shows `seedbox:/home/hd34/btabaska/files /volume1/mounts/seedbox-files fuse.rclone rw,nosuid,nodev,relatime,user_id=0,group_id=0,allow_other`. `ls /volume1/mounts/seedbox-files/` lists `books manual movies music slskd` plus loose grabbed files. Health marker `/var/run/seedbox-mount.ok` reads `2026-07-14T09:45:05-07:00 entries=11` (mtime same, minutes old → watchdog is running).

### Two-strike rule

SFTP connections over WAN can be slow to respond (up to 15–20 s on cold sessions). A single `ls` timeout does NOT mean the mount is dead. The watchdog uses a state file (`/var/run/seedbox-watchdog.fail_count`) so it only tears down the mount after **two consecutive 5-min cycles** where `ls` fails. This prevents the observed failure mode: watchdog destroys a healthy mount that was simply slow to respond.

### Why plain bind (no :rslave)

DSM's kernel rejects `mount --make-shared` on `fuse.rclone` mounts. Docker's `:rslave` propagation requires the source to be shared. Using plain bind means the container sees the mount **at startup only**. After a watchdog remount, the containers are restarted so they re-open their `/seedbox` file descriptors.

!!! note "Validated against live nas (2026-07-14)"
    `docker inspect ... --format '{{.Name}}{{range .Mounts}} {{.Destination}}({{.Propagation}}){{end}}'` shows the `/seedbox` bind propagation is `rprivate` (plain bind, NOT `rslave`) on all five services — confirming the DSM constraint holds.

### DSM Task Scheduler setup

| Task | Type | User | Command | Schedule |
|---|---|---|---|---|
| rclone-seedbox-mount | Triggered | root | `/volume1/scripts/media/rclone-seedbox-mount.sh` | Event: Boot-up |
| rclone-seedbox-watchdog | Scheduled | root | `/volume1/scripts/media/rclone-seedbox-watchdog.sh` | Every 5 min |

Steps:

1. Control Panel → Task Scheduler → Create → **Triggered Task** (boot)
   - User: `root` | Event: `Boot-up`
   - Command: `/volume1/scripts/media/rclone-seedbox-mount.sh`
2. Control Panel → Task Scheduler → Create → **Scheduled Task** (watchdog)
   - User: `root` | Advanced: repeat every **5 minutes**
   - Command: `/volume1/scripts/media/rclone-seedbox-watchdog.sh`

### Operational runbook — if imports stall

1. **Is the mount present?**
   ```bash
   ssh nas 'grep seedbox-files /proc/mounts; ls /volume1/mounts/seedbox-files/'
   ```
   If empty → run mount script manually:
   ```bash
   ssh -t nas 'sudo /volume1/scripts/media/rclone-seedbox-mount.sh'
   ```

2. **Is the SFTP reachable from the NAS?**
   ```bash
   ssh -t nas 'sudo ssh -i /root/.ssh/seedbox_ed25519 btabaska@185.162.184.38 ls files/'
   ```

3. **Are containers seeing /seedbox?**
   ```bash
   ssh -t nas 'sudo /usr/local/bin/docker exec sonarr ls /seedbox/'
   ```
   If empty but mount is present → restart containers:
   ```bash
   ssh -t nas 'sudo /usr/local/bin/docker compose -f /volume1/docker/media-automation/docker-compose.yml restart sonarr radarr lidarr readarr unpackerr'
   ```

4. **Check the log:**
   ```bash
   ssh nas 'tail -50 /var/log/rclone-seedbox.log'
   ```
   Look for `ERROR`, `WARN`, repeated `mounting` lines (indicates recurring drops).

5. **Is the watchdog scheduled?**
   DSM → Control Panel → Task Scheduler → verify both tasks exist and are enabled.

6. **Health marker** (updated by watchdog on every healthy ls):
   ```bash
   ssh nas 'cat /var/run/seedbox-mount.ok'
   ```
   If missing or older than 15 min → mount has been unhealthy for 3+ cycles.

### Monitoring (optional)

- **Uptime Kuma** (docker-11): add a "Command" monitor that SSHes to the NAS and checks the age of `/var/run/seedbox-mount.ok` (alert if >15 min old).
- **Beszel** (docker-10): agent on NAS watches system-level metrics (`beszel-agent` container confirmed running).
- **ntfy** (docker-09): add a curl push to the watchdog's remount path for push alerts.

### Recovery test procedure

```bash
# 1. Verify mount is healthy
ssh nas 'ls /volume1/mounts/seedbox-files/'

# 2. Kill the rclone daemon (simulates drop)
ssh -t nas 'sudo fusermount -uz /volume1/mounts/seedbox-files'

# 3. Verify mount gone
ssh nas 'grep seedbox-files /proc/mounts || echo "gone"'

# 4. Wait one watchdog cycle (up to 5 min) or run manually
ssh -t nas 'sudo /volume1/scripts/media/rclone-seedbox-watchdog.sh'

# 5. Verify restored
ssh nas 'grep seedbox-files /proc/mounts; ls /volume1/mounts/seedbox-files/'

# 6. Verify inside container
ssh -t nas 'sudo /usr/local/bin/docker exec sonarr ls /seedbox/'
```

### Remaining risks

- **DSM OOM**: rclone with `--vfs-cache-mode reads` can cache up to `--buffer-size` per file. This was an acute risk on the stock **4 GB** NAS; since the **20 GB upgrade** (done 2026-07-09) it's low, but with many concurrent imports it's still the thing to watch. If you see rclone killed unexpectedly, reduce `--buffer-size` to `16M` in the mount script.
- **Inherent FUSE fragility on DSM**: Synology's kernel is not a mainstream distro. FUSE mounts can drop after DSM software updates or kernel panics with no warning. The two-strike watchdog bounds the outage to ≤10 min but cannot prevent the initial drop.
- **Alternative if FUSE remains unstable**: Replace the live mount with a short-interval `rclone copy` (every 2–5 min) from `files/{tv,movies,music,books}` into a local staging dir on `/volume1`. \*arrs point at staging. Eliminates FUSE entirely; adds 2–5 min import lag vs live mount. Betty originals keep seeding. This is the recommended fallback if you see >2 FUSE drops per week.

---

## Shared invariants (the self-check at the bottom must verify these)

1. **Identical `/seedbox` bind** on every download-touching service (`sonarr`, `radarr`, `lidarr`, `readarr`, `unpackerr`). Change-one-change-all — the compose uses a YAML anchor (`*seedbox-mount`) so they cannot drift. **DSM note:** plain bind only (no `:rslave` — fuse.rclone cannot be shared/slave). After a watchdog remount, containers are restarted automatically.
2. **Identical PUID/PGID** (from `id <user>`), **TZ=America/New_York**, **restart: unless-stopped**, **/config on `${DOCKER_ROOT}/<app>`** (default `/volume1/docker/<app>`).
3. **Per-service library mounts only** — sonarr sees `/tv` only, radarr `/movies` only, lidarr `/music` only (not a shared `/media` tree).
4. **Exactly ONE scheduled rclone transfer** — `rclone-manual-copy.sh` (manual lane → `/volume1/manual`). \*arr media arrives via **live mount + import**.
5. **Music = Lidarr + Soulseek (split).** Torrents via Deluge (`/seedbox/music`); Soulseek via **slskd on Betty** + **Soularr on NAS** (`/seedbox/slskd`). Optional **beets** tag-only pass on `/music` — Lidarr owns layout.
6. **Readarr → self-hosted rreading-glasses**, permanent root **`/readarr-library`**, copy-on-import to **CWA ingest** (ebook-mgmt workstream).

!!! note "Validated against live nas (2026-07-14)"
    Full mount inspect confirms invariants #1 and #3:
    `/sonarr /config(rprivate) /seedbox(rprivate) /tv(rprivate)`;
    `/radarr /seedbox(rprivate) /config(rprivate) /movies(rprivate)`;
    `/lidarr /config(rprivate) /music(rprivate) /seedbox(rprivate)`;
    `/readarr /config(rprivate) /cwa-book-ingest(rprivate) /readarr-library(rprivate) /scripts(rprivate) /seedbox(rprivate)`;
    `/unpackerr /etc/unpackerr/unpackerr.conf(rprivate) /seedbox(rprivate)`. Each service sees only its own library root, all five share `/seedbox`, and readarr additionally has `/cwa-book-ingest` + `/scripts` (the CWA copy handoff).

---

## RAM-phased rollout checklist (DS920+ ships 4 GB; 20 GB recommended)

- [ ] **Prereqs:** `id <user>` → fill `PUID`/`PGID` and all path vars in `.env`.
- [ ] **Mount first:** rclone.conf; run `rclone-seedbox-mount.sh`; confirm `/volume1/mounts/seedbox-files` lists the seedbox `files/` tree.
- [ ] **Boot + watchdog:** Task Scheduler boot-up = mount; every 5 min = watchdog.
- [ ] **Phase A:** `prowlarr flaresolverr sonarr radarr` → Deluge + mapping; root folders `/tv`, `/movies`.
- [ ] **Phase B:** `lidarr` + `readarr rreading-glasses rreading-glasses-db`.
- [ ] **Phase C:** `unpackerr` → fill API keys in `unpackerr.conf`.
- [ ] **Phase D (Soulseek):** `slskd` on Betty (seed-09) → `soularr` on NAS (nas-29).
- [ ] **Phase E (optional):** `beets` tag layer — `docker compose --profile music-tags run --rm beets beet write` (nas-30).
- [ ] **MusicSeerr (Mac mini):** docker-16 → seed-06 → seed-10 E2E music verification.
- [ ] **Manual lane:** every-15-min Task Scheduler = `rclone-manual-copy.sh`.
- [ ] Run the **self-check** (bottom of this page).

---

## Migrating from Ubuntu (Mac mini)

If you already run Sonarr/Radarr/Lidarr/Readarr on the Ubuntu Docker host, copy their config dirs into `/volume1/docker/<app>/` **before** first container start, then rewire indexers and download clients after boot. Full checklist: `migration-from-ubuntu.md` (repo: `foss-setup/configs/nas/media-automation/migration-from-ubuntu.md`).

Summary of post-import fixes (nas-22):

- Root folders: `/data/tv/` → `/tv`, `/data/movies/` → `/movies`, etc.
- Download client: remove qBittorrent → add remote Deluge on seedbox.
- Indexers: remove Jackett → Prowlarr Full Sync; re-add private indexers from old Jackett JSON as a credential reference.

---

## §3. Download clients — remote Deluge (all \*arrs)

Every \*arr uses the **same remote Deluge** on the seedbox:

- Settings → Download Clients → **+ Deluge**
- Host `185.162.184.38`, Port = daemon port, Password = daemon password
- **Label** per app: `sonarr`, `radarr`, `lidarr`, `readarr`
- **Remove Completed = OFF** in every \*arr (preserves seeding).

---

## §4. Music pipeline — MusicSeerr + Lidarr + Soulseek + optional beets

**MusicSeerr** (Mac mini, docker-16 / seed-06) is the household album request portal. Seerr handles movies/TV only — it has no Lidarr integration. MusicSeerr forwards requests to **Lidarr** on this NAS.

Lidarr imports into **`/music`** (host: `/volume1/music`).

### Torrent path (nas-23)

- **Download client:** remote Deluge, label `lidarr`.
- **Remote Path Mapping:** `/home/hd34/btabaska/files/` → `/seedbox/`.
- **Import source:** `/seedbox/music/`.
- **Root folder:** `/music`.
- **FLAC-preferred with MP3 fallback**; Rename Tracks ON.
- **Music-capable indexer** in Prowlarr.

### Soulseek path (seed-09 + nas-29)

Soulseek is P2P — **slskd runs natively on Betty** (not rootless Docker; port 50300 must bind to the host like Deluge). **Soularr** runs on the NAS next to Lidarr:

1. slskd downloads to `~/files/slskd/` on Betty (`~/slskd-native/.env` + user systemd service).
2. NAS rclone mount exposes it at `/seedbox/slskd/` inside Lidarr/Soularr.
3. Soularr reads Lidarr **Wanted**, searches slskd over Tailscale (`http://betty.<tailnet>:5030`), triggers Lidarr import from `/seedbox/slskd/`.
4. Set `SLSKD_HTTP_IP` in Betty's `.env` to the Tailscale IP so the NAS can reach the slskd API.

Deploy: `scripts/media/install-slskd-native.sh` + `configs/seedbox/slskd-native.example.env`. Full wiring: `foss-setup/configs/seedbox/music-pipeline.md`.

!!! note "Validated against live nas (2026-07-14)"
    `soularr` (`ghcr.io/mrusse/soularr:1.2.2`) is running on the NAS, and the rclone mount exposes `/volume1/mounts/seedbox-files/slskd` (the `slskd` dir is present in the mount listing). slskd itself is native on Betty, so it does not appear in NAS `docker ps` (as designed).

### beets tag layer (nas-30, optional)

Lidarr owns folder layout. beets only refreshes MusicBrainz tags in place:

```bash
docker compose --profile music-tags run --rm beets beet write
```

Copy `beets/config.yaml.example` → `beets/config.yaml`. Schedule weekly via DSM Task Scheduler. **Do not** run `beet import` with move/copy.

> Do NOT change `/music` naming without checking **both** Plex and Rhythmbox/libgpod iPod sync (`/volume1/music` on the host).

!!! note "Validated against live nas (2026-07-14)"
    `beets` (`lscr.io/linuxserver/beets:2.1.0`) is running on the NAS.

---

## §5. Books pipeline — Readarr + rreading-glasses → CWA (+ Libreseerr)

Three roles (see **ebook-mgmt** workstream for migration from ingest-as-root):

| Layer | Tool | Role |
|---|---|---|
| Requests | **Libreseerr** (Mac mini) | Household search & request UI |
| Acquisition & inventory | **Readarr** (NAS) | Deluge grabs, import to **`/readarr-library`** |
| Library & reading | **CWA** (NAS) | Ingest → **`/volume1/books`**, OPDS, Kobo sync |

- **Metadata:** Readarr → `http://<nas>:8787/settings/development` → Provider = `http://rreading-glasses:8788`.
- **Download client:** Deluge, label `readarr`; mapping as in §7.
- **Root folder:** `/readarr-library` (host: `${READARR_LIBRARY}`) — **not** ingest.
- **CWA handoff:** Connect custom script `scripts/media/readarr-copy-to-cwa-ingest.sh` on **On Import** + **On Upgrade** copies to `/cwa-book-ingest` (host: `${CWA_INGEST}`).
- CWA organizes into **`/volume1/books`** for Plex/Kobo. Requires **nas-09** (CWA container running — ingest folder alone is not enough).

!!! note "Validated against live nas (2026-07-14)"
    `readarr` (`linuxserver/readarr:develop-0.4.18.2805-ls157`), `rreading-glasses` (`blampe/rreading-glasses`), `rreading-glasses-db` (`postgres:17.6`, healthy), and `calibre-web-automated` (`ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7`, healthy) are all running. The readarr container inspect confirms both `/cwa-book-ingest` and `/scripts` binds are present (the CWA copy handoff path).

---

## §6. Non-\*arr / manual downloads lane

- Deluge **`manual`** label → `files/manual` on Betty.
- **ONE scheduled job:** `rclone-manual-copy.sh` → `/volume1/manual` (COPY, scoped to `manual/` only).

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
| Readarr | `/readarr-library` | `/volume1/docker/readarr/library` |

**Plex** needs **separate library roots** for TV, Movies, Music, and Books.

Import is a **cross-filesystem COPY** (seedbox mount vs local volume), not a hardlink. Leave Remove Completed OFF.

---

## Final self-check (report violations; don't silently fix)

1. **`/seedbox` bind** on sonarr, radarr, lidarr, readarr, unpackerr (same host path).
2. **Per-volume library mounts:** sonarr → `/tv` only; radarr → `/movies` only; lidarr → `/music` only.
3. **One scheduled rclone job:** manual lane → `/volume1/manual` only.
4. **Lidarr** root `/music`, rename ON; Soulseek via Soularr + `/seedbox/slskd`; optional beets tag-only (no import/move).
5. **Readarr** metadata = `http://rreading-glasses:8788`; root `/readarr-library`; copy script → `/cwa-book-ingest`.
6. **PUID/PGID/TZ** identical; `/config` under `/volume1/docker/<app>`.

```bash
docker inspect sonarr radarr lidarr readarr unpackerr \
  --format '{{.Name}}{{range .Mounts}} {{.Destination}}({{.Propagation}}){{end}}'
```

---

[← NAS reference](index.md)
