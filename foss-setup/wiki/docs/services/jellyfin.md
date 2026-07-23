# jellyfin

Jellyfin — fully-local FOSS media server on Synology DS920+ (media-05)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | https://jellyfin.tabaska.us |
| **Source** | `foss-setup/configs/nas/jellyfin/docker-compose.yml` |
| **Notes** | FOSS fully-local media server (parallel to Plex, no plex.tv dependency). Widget uses API key. |
| **Upstream docs** | <https://jellyfin.org/docs/> |

## About

Jellyfin is a fully-FOSS, fully-local media server running on the NAS (Synology DS920+, `192.168.10.4`) via DSM Container Manager / Docker Compose, project `jellyfin`, reachable at https://jellyfin.tabaska.us (LAN `http://192.168.10.4:8096`). It exists as a plex.tv-independent parallel to Plex (media-05): Plex tethers auth and server discovery to plex.tv, so a plex.tv outage locks out even LAN clients (this actually happened 2026-07-14), whereas Jellyfin has local accounts, LAN discovery and zero external dependency — a title plays from the NAS even with the NAS's WAN access blocked. It runs ALONGSIDE Plex (own port 8096, own container) and does not touch or replace the Plex DSM package. The image is the LinuxServer build `lscr.io/linuxserver/jellyfin:10.11.11` digest-pinned (`@sha256:bb8d372e…`, fix-38/I68 supply-chain posture; LSIO honours the same `PUID=1026`/`PGID=100`/`TZ` convention as the *arr stack). It mounts the SAME libraries Plex serves but READ-ONLY — `/volume2/movies`→`/movies`, `/volume3/tv`→`/tv`, `/volume1/music`→`/music`, `/volume1/youtube`→`/youtube` (all `:ro`; the *arr stack owns writes) — plus a writable config volume at `/volume1/docker/jellyfin/config`. Four libraries are configured: Movies, Shows, Music, and YouTube (a `homevideos`-type library, no external metadata scraping). Hardware transcoding uses the J4125's Intel Quick Sync iGPU: `/dev/dri` is passed in and the container is added to the render group (`group_add: ["937"]`, the owner gid of `/dev/dri/renderD128` on this host) so VA-API can initialise; if VA-API ever fails Jellyfin silently falls back to direct-play / software transcode with no config change. Access is LAN/tailnet-only through the mini's Caddy (`reverse_proxy {$NAS_IP}:8096`, `import local_tls`), with no UPnP auto-port-mapping (remote-access was configured without automatic port mapping, so no WAN port is ever opened). The Homepage `Media`-group tile uses the Jellyfin widget against `http://192.168.10.4:8096` with an admin API key (vault `homepage_widgets.jellyfin_key`). Content — not liveness — is watched by the `nas-jellyfin-serves` verification check, which authenticates with an API key and asserts the Movies and TV libraries actually contain items AND that a real title returns a playable media source (a consumer-end probe, not a `/health` 200). The admin account (`btabaska`) and its credentials are in the vault (`jellyfin.admin_user`/`jellyfin.admin_password`).

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `jellyfin` | `lscr.io/linuxserver/jellyfin:10.11.11@sha256:bb8d372e35d5c4a6cb61d830a06f5b5846528315b97cf5d38b80eea1e430efa7` | `8096:8096` |

## Volumes

| Service | Volume |
|---|---|
| `jellyfin` | `/volume1/docker/jellyfin/config:/config` |
| `jellyfin` | `/volume2/movies:/movies:ro` |
| `jellyfin` | `/volume3/tv:/tv:ro` |
| `jellyfin` | `/volume1/music:/music:ro` |
| `jellyfin` | `/volume1/youtube:/youtube:ro` |

## Troubleshooting

- **A library shows zero items after deploy, or newly-added media never appears** — Trigger a scan (Dashboard > Libraries > Scan All Libraries, or `POST /Library/Refresh` with an API key). Confirm the read-only media mounts are present inside the container: `ssh nas` then `sudo /usr/local/bin/docker exec jellyfin ls /movies /tv /music /youtube`. The mounts are `:ro` by design — if a path is empty, check the host `/volumeN` path still exists and re-`docker compose up -d`.
- **Hardware transcoding is not being used (high CPU on transcode, or "no compatible hardware" in playback logs)** — The Quick Sync device is passed in but must also be enabled in-app: Dashboard > Playback > Transcoding > Hardware acceleration = "Video Acceleration API (VAAPI)", VA-API device `/dev/dri/renderD128`. Confirm the device still exists on the host (`ssh nas 'ls -l /dev/dri'` — expect card0 + renderD128) and that the container is in the render group (`group_add: ["937"]` in docker-compose.yml; the gid must match the owner of /dev/dri/renderD128). If the iGPU is contended by Plex, both can share Quick Sync — sessions queue, they do not fail. As a last resort remove the `devices:`/`group_add:` blocks and redeploy for software-only transcode (playback still works, just costs CPU).
- **Homepage Jellyfin tile shows "API Error" or blank counts** — The widget needs an admin API key, not a user password. Create one at Dashboard > Advanced > API Keys, put it in the homepage stack `.env` as `HOMEPAGE_VAR_JELLYFIN_KEY` (vault `homepage_widgets.jellyfin_key`), and confirm the widget `url` is `http://192.168.10.4:8096` (raw NAS IP, not a container name — Homepage runs on the mini). Note the widget has no `version:` field for Jellyfin < 10.12; only set `version: 2` after upgrading to 10.12+.
- **Clients on the tailnet can reach https://jellyfin.tabaska.us but playback stalls or reports the wrong client IP** — Jellyfin sits behind the mini's Caddy, so it sees the mini's LAN IP for every request. If you need accurate per-client IPs or hit remote-access blocks, add the mini (192.168.10.2) to Dashboard > Networking > Known proxies. Do NOT enable UPnP/automatic port mapping — the service is deliberately LAN/tailnet-only with no public port.

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: jellyfin)
# or over SSH (sudo required): cd /volume1/docker/jellyfin && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
