# komga

Komga — comics + manga reader (read-17)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | https://komga.tabaska.us |
| **Source** | `foss-setup/configs/nas/komga/docker-compose.yml` |
| **Notes** | Comics + manga reader (read-17). JVM app; non-root 1026:100; Comics library under /volume1/comics, Manga library under /volume1/manga (its own DSM share so read-18 Suwayomi can write to it over SMB). Widget uses username/password. |
| **Upstream docs** | <https://komga.org/docs/> · <https://github.com/gotson/komga> |

## About

Komga is a self-hosted comics + manga reader running on the NAS (Synology DS920+, `192.168.10.4`) via DSM Container Manager / Docker Compose, project `komga`, reachable at https://komga.tabaska.us (LAN `http://192.168.10.4:25600`). It exists to give the manually-acquired comics (IPT / GetComics CBZ packs dropped into the library) a real reading server — native `ComicInfo.xml` metadata, OPDS, page streaming, and per-device read-progress — with a huge client ecosystem (Mihon/Tachiyomi, Panels, Paperback, KOReader over OPDS). The image is `gotson/komga:1.25.0` digest-pinned (`@sha256:c4f9885f…`, fix-38/I68 supply-chain posture; pulled on the NAS 2026-07-23). It runs NON-ROOT as `1026:100` (btabaska:users) — the same uid the rest of the NAS stack uses, so CBZ files dropped over SMB and the thumbnails/DB Komga writes stay co-owned; unlike Audiobookshelf, Komga's default listener is the unprivileged port 25600, so there is no port-80 bind trap. The JVM heap is capped at 1G via `JAVA_TOOL_OPTIONS=-Xmx1g` so the Spring-Boot app stays a good neighbour on the shared 19G NAS (Komga must never move to the 8G mini). Two libraries are configured: `Comics` → `/data/Comics` (where `/data` = `/volume1/comics`, the manual CBZ-pack tree) and `Manga` → `/manga` (where `/manga` = the DEDICATED DSM shared folder `/volume1/manga`). Manga was re-homed onto its own share by read-18 because `/volume1/comics` is a plain directory that DSM won't export over SMB — the rig's Suwayomi needs to CIFS-mount the Manga tree read-write to drop grabbed CBZ where Komga scans, so it lives on its own shared folder while Comics stays put. Komga's SQLite DB + generated thumbnails live in a writable config volume at `/volume1/docker/komga/config`. Komga ships with NO default account: the first-run admin is created via the claim API (`POST /api/v1/claim` with `X-Komga-Email`/`X-Komga-Password` headers) — here `btabaska@gmail.com`, roles `ADMIN` + `KOREADER_SYNC` + `KOBO_SYNC` + `PAGE_STREAMING` (vault `komga.admin_email`/`admin_password`). Access is LAN/tailnet-only through the mini's Caddy (`reverse_proxy {$NAS_IP}:25600`, `import local_tls`, Let's Encrypt cert). The Homepage `Reading`-group tile uses the `komga` widget against `http://192.168.10.4:25600` with a USERNAME + PASSWORD (not an API key — vault `homepage_widgets.komga_user`/`komga_pass`), showing live library/series/book counts. Content — not liveness — is watched by the `komga-libraries-consumer` verification check, which authenticates with those same credentials and asserts BOTH the Comics and Manga libraries exist, at least one series is indexed, a real page streams (HTTP 200 image bytes), and the OPDS catalog responds — a consumer-end probe, not an `/actuator/health` 200. A synthetic `Homelab Sample Comic` CBZ was seeded at deploy time to prove the scan → reader → OPDS → widget pipeline; real comics are added by dropping CBZ files into `/volume1/comics/Comics/<Series>/` (one folder per series) and triggering a scan.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `komga` | `gotson/komga:1.25.0@sha256:c4f9885fc077e2e9cd684dc95e8f6cfa5e33b100b46712b2de7f5cc2ff59e6fb` | `25600:25600` |

## Volumes

| Service | Volume |
|---|---|
| `komga` | `/volume1/docker/komga/config:/config` |
| `komga` | `/volume1/comics:/data` |
| `komga` | `/volume1/manga:/manga` |

## Troubleshooting

- **A newly-dropped CBZ doesn't appear, or a library shows zero series** — Komga groups by folder: one folder per series under `/data/Comics` (comics) or `/manga` (manga; Suwayomi writes `/manga/mangas/<source>/<title>/*.cbz`), with the CBZ/CBR files inside. Drop comics as `/volume1/comics/Comics/<Series Name>/<Issue>.cbz`, then trigger a scan: `POST /api/v1/libraries/<library-id>/scan` with basic auth, or Libraries > (⋮) > Scan library files in the UI. Confirm the mounts are present inside the container and readable: `ssh nas` then `sudo /usr/local/bin/docker exec komga ls /data/Comics /manga`. Comics files must be owned `1026:100` (the uid Komga runs as) — `sudo chown -R 1026:100 /volume1/comics` after a bulk drop; Suwayomi-written manga already lands as `btabaska:users` via the CIFS mount.
- **Homepage Komga tile shows "API Error" or blank counts** — The Komga widget authenticates with a USERNAME + PASSWORD, not an API key. Put the admin email + password in the homepage stack `.env` as `HOMEPAGE_VAR_KOMGA_USER` / `HOMEPAGE_VAR_KOMGA_PASS` (vault `homepage_widgets.komga_user` / `komga_pass`), restart the homepage container (env is read at container start), and confirm the widget `url` is `http://192.168.10.4:25600` (raw NAS IP, not a container name — Homepage runs on the mini). Verify the exact path the widget uses: `sudo docker exec homepage wget -qO- --user=<email> --password=<pass> http://192.168.10.4:25600/api/v1/libraries`.
- **Komga is slow to start after a deploy/reboot, or is using a lot of memory** — Komga is a Spring-Boot JVM app — cold start on the NAS J4125 is ~2 minutes (watch for `Started ApplicationKt` in `sudo docker logs komga`); the claim/API endpoints 000/refuse until then. Heap is bounded to 1G by `JAVA_TOOL_OPTIONS=-Xmx1g` in the compose; if a very large library needs more, raise `-Xmx` there and `docker compose up -d`. Never relocate Komga to the 8G mini — keep the JVM on the 19G NAS.
- **You need another Komga account, or forgot the admin password** — The server is already claimed (`GET /api/v1/claim` returns `{"isClaimed":true}`) so the claim flow won't run again. Create additional (e.g. read-only or per-family-member) users in the UI under Server Settings > Users, or `POST /api/v1/users` as admin. The admin credentials are in the vault (`komga.admin_email` / `komga.admin_password`); the same pair drives the Homepage widget and the verification check.

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: komga)
# or over SSH (sudo required): cd /volume1/docker/komga && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
