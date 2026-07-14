# media-automation

Home media-automation stack — Synology DS920+ (Container Manager / Compose)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | — (no web UI / not proxied) |
| **Source** | `foss-setup/configs/nas/media-automation/docker-compose.yml` |

## About

The full home `*arr` acquisition stack, running as the `media-automation` Compose project on the NAS (DS920+, Container Manager) and defined in `foss-setup/configs/nas/media-automation/docker-compose.yml`. It bundles `prowlarr` (indexer manager, with `flaresolverr` for Cloudflare) feeding `sonarr` (TV→`/volume3` `/tv`), `radarr` (movies→`/volume2` `/movies`), `lidarr` (music→`/volume1` `/music`), and the EOL-but-pinned `readarr` (books→`/readarr-library`, pointed at the self-hosted `rreading-glasses` + its `postgres:17.6` DB for metadata since Goodreads' provider died); `unpackerr` extracts archives, `soularr` bridges Lidarr's wants to slskd on the seedbox, and `beets` is an on-demand tag-only layer. The two halves connect off-site: home apps drive the seedbox "Betty" Deluge over its API (`185.162.184.38`) and READ completed downloads through an rclone SFTP mount (`seedbox:/home/hd34/btabaska/files` → `/volume1/mounts/seedbox-files`), which every download-touching container binds at the identical path `/seedbox`; each `*arr` needs a Remote Path Mapping (`/home/hd34/btabaska/files/` → `/seedbox/`) so Deluge-reported paths resolve inside the container. The critical DSM constraint is that `fuse.rclone` cannot satisfy `:rslave` propagation, so the seedbox is a plain bind and download-touching containers must be restarted after any watchdog remount; imports feed downstream to Plex, the CWA book pipeline, and the iPod/Rhythmbox music sync.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `prowlarr` | `lscr.io/linuxserver/prowlarr:2.4.0` | `9696:9696` |
| `flaresolverr` | `ghcr.io/flaresolverr/flaresolverr:v3.5.0` | `8191:8191` |
| `sonarr` | `lscr.io/linuxserver/sonarr:4.0.19` | `8989:8989` |
| `radarr` | `lscr.io/linuxserver/radarr:6.2.1` | `7878:7878` |
| `lidarr` | `lscr.io/linuxserver/lidarr:3.1.0` | `8686:8686` |
| `soularr` | `ghcr.io/mrusse/soularr:1.2.2` | — |
| `beets` | `lscr.io/linuxserver/beets:2.1.0` | `8337:8337` |
| `readarr` | `docker.io/linuxserver/readarr:develop-0.4.18.2805-ls157` | `8787:8787` |
| `rreading-glasses` | `blampe/rreading-glasses@sha256:dd996a1db19ac4ef18df47f1671f608c0f097ed43c4776ebde94dee20c6b43c8` | `8788:8788` |
| `rreading-glasses-db` | `postgres:17.6` | — |
| `unpackerr` | `golift/unpackerr:0.15.2` | — |

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
| `unpackerr` | `./unpackerr/unpackerr.conf:/etc/unpackerr/unpackerr.conf:ro` |
| `unpackerr` | `{'type': 'bind', 'source': '${SEEDBOX_MOUNT:-/volume1/mounts/seedbox-files}', 'target': '/seedbox'}` |

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
- `SEEDBOX_MOUNT`
- `MANUAL_DST`
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

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: media-automation)
# or over SSH (sudo required): cd /volume1/docker/media-automation && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
