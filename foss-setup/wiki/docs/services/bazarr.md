# bazarr

Bazarr — automatic subtitle management for the *arr stack (media-12)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | https://bazarr.tabaska.us |
| **Source** | `foss-setup/configs/nas/bazarr/docker-compose.yml` |
| **Notes** | Subtitle automation for Sonarr + Radarr libraries. |
| **Upstream docs** | <https://www.bazarr.media> · <https://docs.linuxserver.io/images/docker-bazarr/> · <http://192.168.10.4:8989> |

## About

Bazarr is the subtitle *arr — the piece of the download stack that fetches subtitles, which Sonarr and Radarr deliberately do NOT do. It runs on the NAS (Synology DS920+, `192.168.10.4`) via DSM Container Manager / Docker Compose (project `bazarr`), reachable at https://bazarr.tabaska.us (LAN `http://192.168.10.4:6767`). It MUST live on the NAS next to the arrs: Bazarr matches subtitles against the media files on disk, so it has to mount the EXACT SAME container paths the arrs report — `/tv` (= `/volume3/tv`, identical to Sonarr) and `/movies` (= `/volume2/movies`, identical to Radarr). Because the paths are byte-identical to what the arrs hand it over the API, no Bazarr path-mapping is needed. The image is `lscr.io/linuxserver/bazarr:v1.6.0-ls356` digest-pinned (`@sha256:ab401a0f…`, fix-38/I68 supply-chain posture; pulled on the NAS 2026-07-28) and runs as `PUID=1026`/`PGID=100` (`btabaska:users`) — the SAME uid Sonarr/Radarr run as, so the `.srt` files Bazarr writes next to each video stay co-owned and the arrs/players can read them. Config + SQLite DB live in a writable volume at `/volume1/docker/bazarr/config`. Bazarr is wired to BOTH arrs over the API (Settings → Sonarr `http://192.168.10.4:8989`, Settings → Radarr `http://192.168.10.4:7878`, keys from vault `arr_api_keys.sonarr`/`radarr`); on connect it pulled the full libraries (215 movies + 4 series at deploy) and its badges report `sonarr_signalr`/`radarr_signalr` = `LIVE`, meaning it gets a subtitle job the moment either arr grabs something new. An `English` language profile (id 1) is the default for both series and movies, so newly-added media auto-qualifies for subtitle search. The enabled providers are **gestdown** (the Addic7ed API — free, NO account) for the ~99% TV backlog and **yifysubtitles** (free, NO account) for movies. Note the history here (fix-59, 2026-08-03): the original provider **Podnapisi was removed from Bazarr upstream** in v1.6.0 (the provider module is gone and Bazarr's config migration runs `settings.unset('PODNAPISI')`, silently reconciling it out of `enabled_providers`), and **subsource** — despite reading as "free, no account" — now REQUIRES an `api_key` this fleet's vault does not hold (it throttles with `ConfigurationError: Api_key must be specified`), so neither can be used. That regression left `enabled_providers=[]` with zero subtitles EVER fetched against a 2868-episode + 29-movie wanted backlog, while the arr-sync check stayed green — exactly what fix-59 remediated. The vault holds no OpenSubtitles.com credentials or subsource key, so adding either remains an open handoff item for higher coverage/quality. Access is LAN/tailnet-only through the mini's Caddy (`reverse_proxy {$NAS_IP}:6767`, `import local_tls`, Let's Encrypt via Cloudflare DNS-01). The Homepage `Media Automation`-group tile uses the `bazarr` widget against `http://192.168.10.4:6767` with the Bazarr API key (Settings → General → API key; vault `homepage_widgets.bazarr_key`, wired to the homepage stack as `HOMEPAGE_VAR_BAZARR_KEY`), showing live wanted-subtitle counts for episodes and movies. Content — not liveness — is watched by TWO verification checks (`warn` severity), because arr-sync alone was the blind spot that hid the fix-59 outage. `bazarr-synced-from-arrs` authenticates with the API key and asserts the movie library is non-empty (Bazarr really pulled Radarr's catalog, not just booted) AND that BOTH the Sonarr and Radarr SignalR live-links report `LIVE`. `bazarr-providers-can-fetch` (added by fix-59) closes the consumer-end wedge: it asserts at least one provider is enabled, at least one provider status is `Good` (not throttled/mis-configured the way subsource was), AND the episode+movie download-history total is ≥ 1 — i.e. a real subtitle has actually been fetched, the metric that was silently 0. The provider path was proven end-to-end on 2026-08-03: the wanted episode *The Musketeers* S03E10 (no subtitle) was searched, gestdown returned real candidates, and `The.Musketeers.S03E10.720p.x265-ZMNT.en.srt` (score 86.94%) landed next to the video and in Bazarr's download history.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `bazarr` | `lscr.io/linuxserver/bazarr:v1.6.0-ls356@sha256:ab401a0f361cfad328e444838b13d5b334b189d0f556fc91a3623eb581df36df` | `6767:6767` |

## Volumes

| Service | Volume |
|---|---|
| `bazarr` | `/volume1/docker/bazarr/config:/config` |
| `bazarr` | `/volume3/tv:/tv` |
| `bazarr` | `/volume2/movies:/movies` |

## Troubleshooting

- **Bazarr shows a series/movie but never searches subtitles for it** — A language profile only auto-applies to media ADDED after it existed; pre-existing items sync from the arrs with NO profile and are inert. Assign the `English` profile in bulk (Series/Movies → select all → Edit → profile English), or per-item via the API `POST /api/movies` with `radarrid=<id>&profileid=1`. Then trigger a disk scan (`PATCH /api/movies` `action=scan-disk`) so Bazarr recomputes `missing_subtitles`, and a search (`action=search-missing`). Confirm the `.srt` lands next to the video on disk (`ls /volume2/movies/<Movie>/`).
- **Searches log "All providers are throttled" and nothing downloads** — The only enabled provider is Podnapisi, which rate-limits by IP — a burst of manual searches self-throttles it (Bazarr backs off for up to an hour). Reset with `POST /api/providers` `action=reset` and let the SCHEDULED search pick items up rather than hammering manually. The durable fix is provider redundancy: add an OpenSubtitles.com account (Settings → Providers → OpenSubtitles.com, store creds in the vault) so a throttle on one provider isn't a full outage.
- **The Homepage Bazarr tile shows "API Error" or blank counts** — The `bazarr` widget needs the Bazarr API key (Settings → General → API key), not a login. Put it in the homepage stack `.env` as `HOMEPAGE_VAR_BAZARR_KEY` (vault `homepage_widgets.bazarr_key`) and restart the homepage container (env is read at container start). The widget `url` is `http://192.168.10.4:6767` (raw NAS IP — Homepage runs on the mini, not a container name). Verify the exact path the widget uses from inside the container: `docker exec homepage wget -qO- --header="X-API-KEY: <key>" http://192.168.10.4:6767/api/badges` should return JSON with `episodes`/`movies`/`sonarr_signalr`/`radarr_signalr`.

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: bazarr)
# or over SSH (sudo required): cd /volume1/docker/bazarr && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
