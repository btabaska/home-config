# Calibre-Web-Automated (NAS)

Auto-ingest ebooks from `/volume1/docker/calibre-web-automated/ingest` into the
Calibre library at `/volume1/books`. Serves OPDS, Kobo sync, and KOSync on
`:8083` (LAN/Tailscale only).

## Image decision

| Source | Tag | Notes |
|---|---|---|
| **Pinned (use this)** | `ghcr.io/new-usemame/calibre-web-nextgen:v4.0.7` | CVE-2026-7713 fixed; drop-in CWA fork |
| Do not use | `crocodilestick/calibre-web-automated:v4.0.7` | **Never published** on Docker Hub (latest there is v4.0.6) |
| Fallback only | `crocodilestick/calibre-web-automated:v4.0.6` | Works for ingest/OPDS; **disable Kobo sync** (CVE) |

Fork: [Calibre-Web-NextGen](https://github.com/new-usemame/Calibre-Web-NextGen)  
Upstream project: [Calibre-Web-Automated](https://github.com/crocodilestick/Calibre-Web-Automated)

## Deploy from MacBook (nas-09)

Synology SSH often breaks `scp`/`rsync` (`subsystem request failed`). Use **tar
pipe** and **sudo docker**:

```bash
# Transfer (no scp)
cd ~/Documents/Home/foss-setup/configs/nas
tar czf - calibre-web-automated | ssh nas 'tar xzf - -C /tmp/'

# PUID/PGID — must match share owner (`id btabaska` → often 1026:100)
ssh nas 'id btabaska'

# Stage on NAS
ssh -t nas 'sudo mkdir -p /volume1/docker/calibre-web-automated/{config,ingest} /volume1/books'
ssh -t nas 'sudo rsync -a /tmp/calibre-web-automated/ /volume1/docker/calibre-web-automated/'

# First start
ssh -t nas 'cd /volume1/docker/calibre-web-automated && sudo /usr/local/bin/docker compose pull && sudo /usr/local/bin/docker compose up -d'
ssh -t nas 'cd /volume1/docker/calibre-web-automated && sudo /usr/local/bin/docker compose ps'
```

First-run wizard at **http://192.168.10.4:8083** creates `metadata.db` under
`/volume1/books`.

## Ingest behavior

- Drop completed ebooks into **ingest** (Readarr writes to the same path as
  `/cwa-book-ingest` in its container).
- CWA polls the folder (`NETWORK_SHARE_MODE=true`) and imports into
  `/volume1/books`.
- If a file sits in ingest: click **Library Refresh** in the CWA navbar.
- Do not point torrent clients directly at ingest — finish downloads first, then
  move/copy (Readarr import satisfies this).

## Downstream consumers

| Consumer | Path / URL |
|---|---|
| Readarr (nas-24) | Root `/readarr-library`; Connect script copies to ingest | host ingest folder |
| Plex Books | `/volume1/books` |
| KOReader OPDS | `http://<nas>:8083/opds/` (trailing slash) |
| KOSync (read-06) | `http://<nas>:8083/kosync` |

Wiring checklist: `scripts/reading/koreader-cwa-wallabag-wiring.md`
