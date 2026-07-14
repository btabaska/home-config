# Calibre-Web-Automated on the NAS

> Operational wiring for the CWA ebook stack on the Synology NAS — library paths, ingest flow, Kobo/OPDS/KOSync serving, deploy recipe, and image-security decision.

_Source: `foss-setup/configs/nas/calibre-web-automated/README.md` · migrated + validated 2026-07-14_

Calibre-Web-Automated (CWA) auto-ingests ebooks from `/volume1/docker/calibre-web-automated/ingest` into the Calibre library at `/volume1/books`, and serves OPDS, Kobo sync, and KOSync on `:8083` (LAN/Tailscale only — never publish `:8083` publicly).

This page is the **operational** reference. The compose/env/volume table, pinned image, and public URL (`https://books.tabaska.us`) are generated on `services/calibre-web-automated.md` from the compose file — this page complements it and does not duplicate that table.

!!! note "Validated against live nas (2026-07-14)"
    `docker ps` shows `calibre-web-automated` running image `ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7`, `Up 3 days (healthy)`, `restart=always`, created `2026-07-09`. Port `8083/tcp` published on `0.0.0.0:8083` and `[::]:8083`. Live mounts confirm `/volume1/docker/calibre-web-automated/config → /config`, `/volume1/docker/calibre-web-automated/ingest → /cwa-book-ingest`, `/volume1/books → /calibre-library`.

## Image decision

| Source | Tag | Notes |
|---|---|---|
| **Pinned (use this)** | `ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7` | CVE-2026-7713 fixed; drop-in CWA fork |
| Do not use | `crocodilestick/calibre-web-automated:v4.0.7` | **Never published** on Docker Hub (latest there is v4.0.6) |
| Fallback only | `crocodilestick/calibre-web-automated:v4.0.6` | Works for ingest/OPDS; **disable Kobo sync** (CVE) |

- Fork (in use): Calibre-Web-NextGen — https://github.com/new-usemame/Calibre-Web-NextGen
- Upstream project: Calibre-Web-Automated — https://github.com/crocodilestick/Calibre-Web-Automated

Rationale: upstream `crocodilestick/calibre-web-automated` on Docker Hub stops at `v4.0.6`. **CVE-2026-7713** (Kobo auth-token IDOR) is fixed in `v4.0.7`, which is published only on the community fork. The fork is a drop-in replacement — same `/config`, `/calibre-library`, `/cwa-book-ingest` mounts. With `v4.0.7+`, Kobo sync and KOSync are safe to enable (`read-06`).

Release with the fix: https://github.com/new-usemame/Calibre-Web-NextGen/releases/tag/v4.0.7

## Deployed container facts

| Fact | Value |
|---|---|
| Container / project name | `calibre-web-automated` |
| PUID / PGID | `1026` / `100` (must match the DSM user that owns `/volume1/books`) |
| TZ | `America/New_York` |
| Restart policy | `always` |
| Calibre config dir (inside container) | `/config/.config/calibre` (`CALIBRE_CONFIG_DIR`) |
| App DB | `metadata.db` lives under `/volume1/books` (created by first-run wizard) |

!!! note "Validated against live nas (2026-07-14)"
    `id btabaska` → `uid=1026(btabaska) gid=100(users)`, matching `PUID=1026` / `PGID=100` in the running container. `/volume1/books/metadata.db` exists (`512000` bytes, owner `btabaska:users`, mode `rwxrwx---`) with live `-wal` / `-shm` files (WAL journaling active), confirming the library is initialized and actively written.

## `NETWORK_SHARE_MODE` — live value differs from the compose file

!!! note "Validated against live nas (2026-07-14) — CORRECTION"
    The source README and the on-disk `docker-compose.yml` set `NETWORK_SHARE_MODE=true`, but the **live container runs with `NETWORK_SHARE_MODE=false`**. This is a deliberate operational override (the SMB/CIFS-backed share's inotify watcher is unreliable, so the built-in watcher is turned off and ingest is driven by a manual/scheduled **Library Refresh** instead). Treat `false` as the effective value; if you `docker compose up -d` from the unedited compose file it will flip back to `true` — re-apply the override after any redeploy.

## Deploy from MacBook (`nas-09`)

Synology SSH often breaks `scp`/`rsync` with `subsystem request failed`. Use a **tar pipe** for transfer and **sudo docker** on the NAS:

```bash
# Transfer (no scp)
cd ~/Documents/Home/foss-setup/configs/nas
tar czf - calibre-web-automated | ssh nas 'tar xzf - -C /tmp/'

# PUID/PGID — must match share owner (id btabaska → 1026:100)
ssh nas 'id btabaska'

# Stage on NAS
ssh -t nas 'sudo mkdir -p /volume1/docker/calibre-web-automated/{config,ingest} /volume1/books'
ssh -t nas 'sudo rsync -a /tmp/calibre-web-automated/ /volume1/docker/calibre-web-automated/'

# First start
ssh -t nas 'cd /volume1/docker/calibre-web-automated && sudo /usr/local/bin/docker compose pull && sudo /usr/local/bin/docker compose up -d'
ssh -t nas 'cd /volume1/docker/calibre-web-automated && sudo /usr/local/bin/docker compose ps'
```

First-run wizard at **http://192.168.10.4:8083** creates `metadata.db` under `/volume1/books`.

To upgrade: bump the image tag in `docker-compose.yml`, read the release notes, then:

```bash
ssh -t nas 'cd /volume1/docker/calibre-web-automated && sudo /usr/local/bin/docker compose pull && sudo /usr/local/bin/docker compose up -d'
```

## Ingest behavior

- Drop completed ebooks into the **ingest** folder — `/volume1/docker/calibre-web-automated/ingest` on the host, mounted as `/cwa-book-ingest` in the container. Readarr writes to this same path.
- CWA polls the folder and imports into `/volume1/books` (`/calibre-library`).
- If a file sits in ingest and is not picked up, click **Library Refresh** in the CWA navbar (this is the primary trigger given `NETWORK_SHARE_MODE=false`).
- **Do not** point torrent clients directly at ingest — finish downloads first, then move/copy. Readarr import satisfies this.

!!! note "Validated against live nas (2026-07-14)"
    The ingest folder `/volume1/docker/calibre-web-automated/ingest` exists and is empty (owner `btabaska:users`), i.e. no stuck imports at time of check.

## Downstream consumers

| Consumer | Path / URL |
|---|---|
| Readarr (`nas-24`) | Root `/readarr-library`; a Connect (Custom Script) copies imported files into the host ingest folder |
| Plex Books | `/volume1/books` |
| KOReader OPDS | `http://<nas>:8083/opds/` (trailing slash required) |
| KOSync (`read-06`) | `http://<nas>:8083/kosync` |

Wiring checklist (repo): `guides/koreader-cwa-wallabag.md`. End-to-end KOReader/CWA/Wallabag guide: `guides/koreader-cwa-wallabag.md`.

## Security posture

- Keep CWA **LAN/Tailscale-only** — do not expose `:8083` publicly. The public `https://books.tabaska.us` hostname is fronted by the reverse-proxy/Tailscale path documented on the generated service page, not a raw port exposure.
- Kobo sync and KOSync are safe to enable only on `v4.0.7+` (CVE-2026-7713 fixed). If you ever fall back to `crocodilestick/...:v4.0.6`, disable Kobo sync.
- Back up `/volume1/docker/calibre-web-automated/config` (small Tier-1 CWA app DB) and `/volume1/books/metadata.db`.

---

[← NAS reference](index.md)
