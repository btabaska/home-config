# media-automation

Home media-automation stack — Synology DS920+ (Container Manager / Compose)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | — (no web UI / not proxied) |
| **Source** | `foss-setup/configs/nas/media-automation/docker-compose.yml` |

## About

The full home `*arr` acquisition stack, running as the `media-automation` Compose project on the NAS (DS920+, Container Manager) and defined in `foss-setup/configs/nas/media-automation/docker-compose.yml`. It bundles `prowlarr` (indexer manager, with `flaresolverr` for Cloudflare) feeding `sonarr` (TV→`/volume3` `/tv`), `radarr` (movies→`/volume2` `/movies`), `lidarr` (music→`/volume1` `/music`), and the EOL-but-pinned `readarr` (books→`/readarr-library`, pointed at the self-hosted `rreading-glasses` + its `postgres:17.6` DB for metadata since Goodreads' provider died); `unpackerr` extracts archives, `soularr` bridges Lidarr's wants to slskd on the seedbox, and `beets` is an on-demand tag-only layer. The books path is mid-cutover (`docs/books-metadata-cutover-2026-07-20.md`, bmig-01…06): a second metadata instance `rreading-glasses-hc` (:8789, Hardcover mode, own `rreading_glasses_hc` database in the shared postgres, token at vault `books.hardcover_api_token` — expires every Jan 1) runs in PARALLEL with the goodreads one, and `bookshelf` (:8790, `ghcr.io/pennydreadful/bookshelf` hardcover variant, digest-pinned, API key at vault `arr_api_keys.bookshelf`, same UI login as readarr) consumes it as the readarr replacement — mirroring readarr's EPUB-Preferred profile, foreign-language release blocklist, Deluge client (its OWN `bookshelf`/`bookshelf-imported` categories — deliberately NOT readarr's, to stop completed-download cross-tracking), remote path mapping, and the CWA-ingest Connect script; until the bmig-05 cutover the old readarr→CWA path keeps running untouched and bookshelf holds no monitored items. Beware: POSTing a root folder to bookshelf/readarr triggers an immediate disk scan that auto-adopts matched files into the library — under Hardcover quota pressure this mints junk/duplicate records (bmig-03 must pace one author at a time). The two halves connect off-site: home apps drive the seedbox "Betty" Deluge over its API via the tailnet (`100.119.134.94:5945` — since fix-21 Deluge binds loopback on Betty and the public IP exposes nothing; the NAS Tailscale package must stay in TUN mode) and READ completed downloads through an rclone SFTP mount (`seedbox:/home/hd34/btabaska/files` → `/volume1/mounts/seedbox-files`), which every download-touching container binds at the identical path `/seedbox`; each `*arr` needs a Remote Path Mapping (`/home/hd34/btabaska/files/` → `/seedbox/`) so Deluge-reported paths resolve inside the container. The critical DSM constraint is that `fuse.rclone` cannot satisfy `:rslave` propagation, so the seedbox is a plain bind and download-touching containers must be restarted after any watchdog remount; imports feed downstream to Plex, the CWA book pipeline, and the iPod/Rhythmbox music sync.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `prowlarr` | `lscr.io/linuxserver/prowlarr:2.4.0` | `9696:9696` |
| `flaresolverr` | `ghcr.io/flaresolverr/flaresolverr:v3.5.0` | `8191:8191` |
| `sonarr` | `lscr.io/linuxserver/sonarr:4.0.19` | `8989:8989` |
| `radarr` | `lscr.io/linuxserver/radarr:6.3.0` | `7878:7878` |
| `lidarr` | `lscr.io/linuxserver/lidarr:3.1.0` | `8686:8686` |
| `soularr` | `ghcr.io/mrusse/soularr:1.2.2` | — |
| `beets` | `lscr.io/linuxserver/beets:2.1.0` | `8337:8337` |
| `readarr` | `docker.io/linuxserver/readarr:develop-0.4.18.2805-ls157` | `8787:8787` |
| `rreading-glasses` | `blampe/rreading-glasses@sha256:dd996a1db19ac4ef18df47f1671f608c0f097ed43c4776ebde94dee20c6b43c8` | `8788:8788` |
| `rreading-glasses-hc` | `local/rreading-glasses:hardcover-batch5-a2939b6` | `8789:8788` |
| `rreading-glasses-db` | `postgres:17.6` | — |
| `bookshelf` | `ghcr.io/pennydreadful/bookshelf:hardcover-v0.4.20.129@sha256:388eecc94362580eae31ee0a454be6af516f8a311f8432a521c202fb475f4359` | `8790:8787` |
| `unpackerr` | `golift/unpackerr:0.15.2` | `5656:5656` |
| `whisparr` | `ghcr.io/hotio/whisparr@sha256:dfa198dc37a89f9f6b7a0fad39e66cfaa1153659a80e22fd9d9475b8b08bcac5` | `6969:6969` |

## Volumes

| Service | Volume |
|---|---|
| `prowlarr` | `${DOCKER_ROOT:-/volume1/docker}/prowlarr/config:/config` |
| `sonarr` | `${DOCKER_ROOT:-/volume1/docker}/sonarr/config:/config` |
| `sonarr` | `${TV_LIBRARY:-/volume3/tv}:/tv` |
| `sonarr` | `{'type': 'bind', 'source': '${SEEDBOX_MOUNT:-/volume1/mounts/seedbox-files}', 'target': '/seedbox'}` |
| `radarr` | `${DOCKER_ROOT:-/volume1/docker}/radarr/config:/config` |
| `radarr` | `${MOVIES_LIBRARY:-/volume2/movies}:/movies` |
| `radarr` | `{'type': 'bind', 'source': '${SEEDBOX_MOUNT:-/volume1/mounts/seedbox-files}', 'target': '/seedbox'}` |
| `lidarr` | `${DOCKER_ROOT:-/volume1/docker}/lidarr/config:/config` |
| `lidarr` | `${MUSIC_LIBRARY:-/volume1/music}:/music` |
| `lidarr` | `{'type': 'bind', 'source': '${SEEDBOX_MOUNT:-/volume1/mounts/seedbox-files}', 'target': '/seedbox'}` |
| `soularr` | `${DOCKER_ROOT:-/volume1/docker}/soularr:/data` |
| `soularr` | `{'type': 'bind', 'source': '${SEEDBOX_MOUNT:-/volume1/mounts/seedbox-files}', 'target': '/seedbox'}` |
| `beets` | `${DOCKER_ROOT:-/volume1/docker}/beets:/config` |
| `beets` | `${MUSIC_LIBRARY:-/volume1/music}:/music` |
| `readarr` | `${DOCKER_ROOT:-/volume1/docker}/readarr/config:/config` |
| `readarr` | `${READARR_LIBRARY:-/volume1/docker/readarr/library}:/readarr-library` |
| `readarr` | `${CWA_INGEST:-/volume1/docker/calibre-web-automated/ingest}:/cwa-book-ingest` |
| `readarr` | `${DOCKER_ROOT:-/volume1/docker}/readarr/scripts:/scripts:ro` |
| `readarr` | `{'type': 'bind', 'source': '${SEEDBOX_MOUNT:-/volume1/mounts/seedbox-files}', 'target': '/seedbox'}` |
| `rreading-glasses-db` | `${DOCKER_ROOT:-/volume1/docker}/rreading-glasses/postgres:/var/lib/postgresql/data` |
| `bookshelf` | `${DOCKER_ROOT:-/volume1/docker}/bookshelf/config:/config` |
| `bookshelf` | `${READARR_LIBRARY:-/volume1/docker/readarr/library}:/readarr-library` |
| `bookshelf` | `${CWA_INGEST:-/volume1/docker/calibre-web-automated/ingest}:/cwa-book-ingest` |
| `bookshelf` | `${DOCKER_ROOT:-/volume1/docker}/readarr/scripts:/scripts:ro` |
| `bookshelf` | `{'type': 'bind', 'source': '${SEEDBOX_MOUNT:-/volume1/mounts/seedbox-files}', 'target': '/seedbox'}` |
| `unpackerr` | `./unpackerr/unpackerr.conf:/etc/unpackerr/unpackerr.conf:ro` |
| `unpackerr` | `{'type': 'bind', 'source': '${SEEDBOX_MOUNT:-/volume1/mounts/seedbox-files}', 'target': '/seedbox'}` |
| `whisparr` | `${DOCKER_ROOT:-/volume1/docker}/whisparr/config:/config` |
| `whisparr` | `${WHISPARR_LIBRARY:-/volume1/stash/root/whisparr}:/data` |
| `whisparr` | `{'type': 'bind', 'source': '${SEEDBOX_MOUNT:-/volume1/mounts/seedbox-files}', 'target': '/seedbox'}` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `PUID`
- `PGID`
- `TZ`
- `TV_LIBRARY`
- `MOVIES_LIBRARY`
- `MUSIC_LIBRARY`
- `DOCKER_ROOT`
- `CWA_INGEST`
- `READARR_LIBRARY`
- `WHISPARR_LIBRARY`
- `SEEDBOX_MOUNT`
- `MANUAL_DST`
- `HARDCOVER_API_TOKEN`
- `RG_DB_NAME`
- `RG_DB_USER`
- `RG_DB_PASSWORD`
- `SOULARR_INTERVAL`

## Troubleshooting

- **Radarr shows a movie as imported (hasFile=True) but the file is only ~6-24 MB and Plex shows nothing — a release's junk `sample.*` was imported as the feature.** — Delete the sample-sized file, blocklist/re-grab the release, and confirm Radarr's Minimum size / sample-rejection quality rules are set so tiny files are filtered. The `arr-plex-journey.py` #6 check (tmdb/tvdb external-id coverage) is what surfaces this 'green but not watchable' gap.
- **Sonarr search UI freezes / interactive search returns ~0 grabs; app becomes unresponsive.** — SQLite-lock search-freeze class — restart sonarr (`sudo docker restart sonarr` on the NAS) to clear the wedged DB lock. Note IPT-only indexers legitimately return near-zero grabs; verify Prowlarr has additional capable indexers + the FlareSolverr proxy (`http://flaresolverr:8191`) attached before assuming a freeze.
- **Downloads sit in *arr queues forever waiting on extraction, but the unpackerr container still reports 'Up'.** — unpackerr can silently wedge its poller while the process stays up. The compose already adds a healthcheck probing `http://localhost:5656/metrics` so a fully-wedged process flips the container to 'unhealthy' (paged via containers-health-nas); if wedged, `sudo docker restart unpackerr`. Confirm the `[webserver]` block stays enabled in `./unpackerr/unpackerr.conf` or the healthcheck can't fire.
- **After a seedbox rclone remount, *arr imports fail with I/O / EBADF errors even though `/seedbox` looks mounted.** — The fuse.rclone bind cannot use rslave propagation, so containers hold a stale mount after a watchdog remount. Restart every download-touching container (`sudo docker restart sonarr radarr lidarr readarr unpackerr`) — the remount watchdog normally does this automatically.
- **Readarr book searches 400 / metadata lookups fail, or the rreading-glasses container errors on credential generation.** — rreading-glasses ships only rolling tags and is pinned by digest; Goodreads auth changes can break credential generation. Refresh the digest deliberately: `docker buildx imagetools inspect blampe/rreading-glasses:latest`, update the `@sha256:` pin in the compose, then `docker compose up -d rreading-glasses`. Ensure Readarr's Metadata Provider Source (Settings > Development, hidden page) points at `http://rreading-glasses:8788`.
- **rreading-glasses-hc (:8789) searches return empty `[]` while the container is Up, with `403 top_level_limit_exceeded` or `429` batched-query errors in its logs.** — Two distinct causes. 403 top_level_limit_exceeded = the Hardcover API caps GraphQL requests at 5 top-level queries (since 2026-07-18); the published `:hardcover` image batches 25 and is broken — the NAS runs a temporary local build `local/rreading-glasses:hardcover-batch5-a2939b6` (upstream main a2939b6 + a one-line batch-size patch, built on the mini; see the IMAGE note in `configs/nas/media-automation/docker-compose.yml` and upstream issue blampe/rreading-glasses#574 — swap back to the upstream digest once fixed, task books-hc-upstream-swap). 429 = Hardcover's ~60 req/min quota, normal on a cold cache while background author refreshes run; it settles as the postgres cache warms. Separately, the token at vault `books.hardcover_api_token` EXPIRES every Jan 1 — renew at hardcover.app → Settings → Hardcover API, update `HARDCOVER_API_TOKEN` in the stack `.env`, and recreate the container.

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: media-automation)
# or over SSH (sudo required): cd /volume1/docker/media-automation && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
