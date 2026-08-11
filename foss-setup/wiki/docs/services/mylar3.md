# mylar3

Mylar3 — western-comics automation (read-21)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | https://mylar.tabaska.us |
| **Source** | `foss-setup/configs/nas/mylar3/docker-compose.yml` |
| **Notes** | Western-comics acquisition *arr (read-21..25) — Sonarr's role for comics. LSIO container on the NAS; PUID/PGID 1026:100 (matches Komga so grabbed CBZ stay readable). Primary acquisition = built-in GetComics DDL over plain HTTPS (read-22, no indexer/download client); torrent safety-net via Prowlarr app-sync + off-site Betty Deluge (read-23, best-effort). ComicVine API key = metadata authority (identity/catalog only, like TheTVDB to Sonarr). Output lands in /volume1/comics/Comics/<Series>/ which Komga's Comics library scans. Completes the comics/manga row — Mylar3 = western comics, Suwayomi = manga, Komga = shared reader. Homepage widget uses the Mylar3 API key. |
| **Upstream docs** | <https://github.com/mylar3/mylar3> · <https://docs.linuxserver.io/images/docker-mylar3/> |

## About

Mylar3 is the western-COMICS acquisition *arr — it plays Sonarr's role (monitor + search + grab + file + metadata) for comic books, the piece Suwayomi (read-18, manga only) deliberately does not cover. It runs on the NAS (Synology DS920+, `192.168.10.4`) via DSM Container Manager / Docker Compose (project `mylar3`), reachable at https://mylar.tabaska.us (LAN `http://192.168.10.4:8090`). It MUST live on the NAS: its output tree `/volume1/comics` is a plain (non-SMB) directory, so unlike the read-18 manga share the mini/rig can't cleanly mount it as a write target — the grabber has to sit next to the files. The image is `lscr.io/linuxserver/mylar3:latest` digest-pinned (`@sha256:4e105bb0…`, fix-38/I68 supply-chain posture; pulled on the NAS 2026-07-27) and runs as `PUID=1026`/`PGID=100` (`btabaska:users`) — the SAME uid Komga runs as, so grabbed CBZ stay readable by the reader and NAS ACLs hold. Two binds: a writable config volume at `/volume1/docker/mylar3/config` (SQLite DB, `config.ini`, logs) and the comics output tree `/volume1/comics` → `/comics`, where Mylar files each issue as `/comics/Comics/<Series>/<Issue>.cbz` — exactly the path Komga's `Comics` library (`/data/Comics` = `/volume1/comics`) scans. METADATA authority is ComicVine: Mylar3 needs a free ComicVine API key (`comicvine.gamespot.com/api`, vault `comicvine.api_key`, wired in `config.ini`) as its identity/catalog source — ComicVine is to Mylar3 what TheTVDB is to Sonarr; it hosts NO files, only series/issue identity and cover art. ACQUISITION is two-tier. PRIMARY (read-22) is the built-in **GetComics DDL** provider: plain HTTPS direct-download straight from the NAS with NO indexer and NO download client — Mylar matches a series against ComicVine, finds the issue on GetComics, downloads the CBZ, and files it into `/comics/Comics/<Series>/`. FALLBACK (read-23, best-effort) is a torrent safety-net for titles GetComics doesn't carry, reusing existing infra with no new indexers: Mylar3 is registered as a Prowlarr Application (Full Sync) so Prowlarr auto-pushes ONLY comics-category (Torznab 7030) indexers into it — category-gated exactly like Whisparr's XXX gating; of the live indexers, IPTorrents / MyAnonamouse / RetroToon carry comics (MyAnonamouse is the clean English one) — and Mylar's torrent client points at the off-site Betty Deluge over Tailscale with a dedicated `mylar` category (identical remote-path-mapping to the other *arrs). Access is LAN/tailnet-only through the mini's Caddy (`reverse_proxy {$NAS_IP}:8090`, `import local_tls`, Let's Encrypt via Cloudflare DNS-01). The Homepage `Reading`-group tile uses the `mylar` widget against `http://192.168.10.4:8090` with the Mylar3 API key (Settings → Web Interface → API, `api_enabled = True`; vault `mylar3.api_key`, wired to the homepage stack as `HOMEPAGE_VAR_MYLAR_KEY`), showing live series / issues / wanted counts. Content — not liveness — is watched by the `mylar3-feeds-komga` verification check (read-24, `warn`-severity because acquisition is best-effort, mirroring `suwayomi-feeds-komga`): it walks the whole chain — Mylar3's API answers (`getVersion` `success:true`), at least one CBZ has actually landed under `/volume1/comics/Comics` (a live-but-empty tree means nothing flowed even while both servers look green), and Komga's `Comics` library is available with ≥ the baseline indexed series count (i.e. the read-22 grab is really readable). At the read-22 milestone the whole path was proven end to end: a ComicVine-matched series was added, an issue grabbed via GetComics DDL, the CBZ filed to `/volume1/comics/Comics/<Series>/` owned `1026:100`, and Komga scanned it into a readable book. This completes the comics/manga row of the media model: **Mylar3 = western-comics acquisition, Suwayomi = manga acquisition, Komga = the shared reader.**

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `mylar3` | `lscr.io/linuxserver/mylar3:latest@sha256:4e105bb091e587bfa37d3d38b6e924695379e2b043e82037d33101396fa5eafc` | `8090:8090` |

## Volumes

| Service | Volume |
|---|---|
| `mylar3` | `/volume1/docker/mylar3/config:/config` |
| `mylar3` | `/volume1/comics:/comics` |
| `mylar3` | `/volume1/mounts/seedbox-files:/seedbox` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `MYLAR3_COMICVINE_API_KEY`

## Troubleshooting

- **A monitored series never grabs anything, or new issues aren't downloading** — Mylar only grabs issues it has both a ComicVine match AND a provider result for. First confirm the ComicVine key is live (Settings → Metadata; a bad/expired key = no matches at all — vault `comicvine.api_key`). Then check the GetComics DDL provider is enabled (Settings → Providers → the built-in DDL toggle) — it's the primary path and needs no indexer. GetComics doesn't carry every title; for the rest, the torrent fallback must be wired (Prowlarr Application Full Sync pushing comics-category indexers + the Betty Deluge client) — see the Prowlarr/seedbox pages. Force a search from the series page (Search → "Search for issues") and watch `sudo /usr/local/bin/docker logs mylar3` for the match/grab lines.
- **A grabbed CBZ isn't showing up in Komga** — Mylar files to `/volume1/comics/Comics/<Series>/<Issue>.cbz`; Komga's `Comics` library scans `/data/Comics` (= `/volume1/comics`). Confirm the file exists and is owned `1026:100`: `ssh nas 'sudo ls -l /volume1/comics/Comics/<Series>/'` (a wrong owner = Komga can't read it — `sudo chown -R 1026:100 /volume1/comics`). Komga watches the filesystem but you can force it: `POST https://komga.tabaska.us/api/v1/libraries/<comics-lib-id>/scan` (basic auth). If the CBZ is on disk but Komga never indexes it, the Komga side is the problem (see the komga page).
- **The Homepage Mylar3 tile shows "API Error" or blank counts** — The `mylar` widget needs the Mylar3 API key, not a login. Enable it in Mylar (Settings → Web Interface → check "Enable API", note the key; `api_enabled = True` in `config.ini`), put it in the homepage stack `.env` as `HOMEPAGE_VAR_MYLAR_KEY` (vault `mylar3.api_key`), and restart the homepage container (env is read at container start). Verify the exact path the widget uses: `sudo docker exec homepage wget -qO- 'http://192.168.10.4:8090/api?apikey=<key>&cmd=getVersion'` should return `success:true`. The widget `url` is `http://192.168.10.4:8090` (raw NAS IP — Homepage runs on the mini, not a container name).

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: mylar3)
# or over SSH (sudo required): cd /volume1/docker/mylar3 && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
