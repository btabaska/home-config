# audiobookshelf

Audiobookshelf — self-hosted audiobook + podcast server on the Synology DS920+ (read-16).

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | https://abs.tabaska.us |
| **Source** | `foss-setup/configs/nas/audiobookshelf/docker-compose.yml` |
| **Notes** | Audiobooks + podcasts server (read-16). Non-root; internal PORT=13378. Widget uses an API key. |
| **Upstream docs** | <https://www.audiobookshelf.org/docs> |

## About

Audiobookshelf is a self-hosted audiobook + podcast server running on the NAS (Synology DS920+, `192.168.10.4`) via DSM Container Manager / Docker Compose, project `audiobookshelf`, reachable at https://abs.tabaska.us (LAN `http://192.168.10.4:13378`). It exists to give the MAM audiobooks a real home with native iOS/Android apps and cross-device progress sync, and to replace the desktop-only gPodder path for podcasts — ABS subscribes to podcast RSS feeds and downloads episodes server-side into its own library. The image is `ghcr.io/advplyr/audiobookshelf:2.35.1` digest-pinned (`@sha256:1eef6716…`, fix-38/I68 supply-chain posture; pulled on the NAS 2026-07-23). It runs NON-ROOT as `1026:100` (btabaska:users) — the same uid the rest of the NAS stack uses, so audiobook files dropped over SMB and files ABS writes stay co-owned. The official ABS image defaults its internal listener to privileged port 80, which a non-root user CANNOT bind (it crashes with `listen EACCES`); the compose therefore sets `PORT=13378` to move the listener to an unprivileged port the `1026:100` user can bind, and maps the host 1:1 (`13378:13378`). Two libraries are configured, each pointed at a DEDICATED tree that is NOT one of the *arr/calibre-managed trees: `Audiobooks` → `/volume1/audiobooks` (book type; MAM audiobooks land here) and `Podcasts` → `/volume1/podcasts` (podcast type; ABS-managed downloads). `/volume1/books` is calibre-web-automated's ebook library (it has its own `metadata.db`) and ABS never touches it. Config + metadata live in writable volumes at `/volume1/docker/audiobookshelf/{config,metadata}`. Access is LAN/tailnet-only through the mini's Caddy (`reverse_proxy {$NAS_IP}:13378`, `import local_tls`). The Homepage `Reading`-group tile uses the `audiobookshelf` widget against `http://192.168.10.4:13378` with a long-lived API key (vault `homepage_widgets.audiobookshelf_key`, minted post-first-run under Settings > API Keys). Content — not liveness — is watched by the `audiobookshelf-libraries-consumer` verification check, which authenticates with that same API key and asserts `/api/libraries` returns BOTH a book-type and podcast-type library AND that the Audiobooks library holds >=1 real item (a consumer-end probe, not a `/status` 200). The admin (root) account (`admin`) and its credentials + the API key are in the vault (`audiobookshelf.admin_user`/`admin_password`/`api_key`).

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `audiobookshelf` | `ghcr.io/advplyr/audiobookshelf:2.35.1@sha256:1eef6716183c52abafe5405e7d6be8390248ecd59c7488c44af871757ac8fc4d` | `13378:13378` |

## Volumes

| Service | Volume |
|---|---|
| `audiobookshelf` | `/volume1/docker/audiobookshelf/config:/config` |
| `audiobookshelf` | `/volume1/docker/audiobookshelf/metadata:/metadata` |
| `audiobookshelf` | `/volume1/audiobooks:/audiobooks` |
| `audiobookshelf` | `/volume1/podcasts:/podcasts` |

## Troubleshooting

- **The container restart-loops right after deploy; logs end with `Error: listen EACCES: permission denied 0.0.0.0:80`** — This is the non-root-can't-bind-port-80 trap. The official image defaults to internal port 80, but the compose runs ABS as `user: "1026:100"` and an unprivileged user cannot bind ports <1024. The fix (already in the compose) is `environment: - PORT=13378` plus a `13378:13378` port mapping so ABS listens on an unprivileged port. If you ever drop the `PORT` env, either restore it or remove the `user:` line to run as root (less preferred). Verify with `ssh nas` then `sudo /usr/local/bin/docker logs audiobookshelf | grep Listening` — expect `Listening on port :13378`.
- **A newly-added audiobook doesn't appear, or the Audiobooks library shows zero items** — Drop audiobooks under `/volume1/audiobooks/<Author or Title>/…` (one folder per book) and trigger a scan: `POST /api/libraries/<audiobooks-lib-id>/scan` with a Bearer API key, or Settings > Libraries > (⋮) > Scan in the UI. Do NOT point the library at `/volume1/books` — that is calibre-web-automated's ebook tree, not audiobooks. Confirm the mount is present inside the container: `sudo /usr/local/bin/docker exec audiobookshelf ls /audiobooks /podcasts`.
- **A podcast is subscribed but no episodes download** — Add the podcast by RSS feed (Settings > Libraries > Podcasts > Add, or `POST /api/podcasts` after `POST /api/podcasts/feed`), then queue an episode with `POST /api/podcasts/<item-id>/download-episodes`. Episodes land in `/volume1/podcasts/<Podcast Title>/`. Enable `autoDownloadEpisodes` on the podcast for the newest episode to fetch automatically on the schedule. Confirm write access: `/volume1/podcasts` is owned `1026:100` `775`, and ABS runs as `1026:100`, so it can write.
- **Homepage Audiobookshelf tile shows "API Error" or blank counts** — The widget needs an API key, not the login password. Create one at Settings > Users > (your user) > API Keys (or `POST /api/api-keys`), put it in the homepage stack `.env` as `HOMEPAGE_VAR_ABS_KEY` (vault `homepage_widgets.audiobookshelf_key`), restart the homepage container, and confirm the widget `url` is `http://192.168.10.4:13378` (raw NAS IP, not a container name — Homepage runs on the mini). Verify the exact path the widget uses from inside the container: `docker exec homepage wget -qO- --header="Authorization: Bearer <key>" http://192.168.10.4:13378/api/libraries`.

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: audiobookshelf)
# or over SSH (sudo required): cd /volume1/docker/audiobookshelf && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
