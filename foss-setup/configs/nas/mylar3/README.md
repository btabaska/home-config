# Mylar3 — western-comics automation (read-21)

Mylar3 is the comics-native `*arr` (monitor + grabber + filer — the role Sonarr plays for TV,
for western comics). It feeds Komga's **Comics** library (read-17); manga is handled separately
by Suwayomi (read-18). ComicVine is the metadata authority — identity/catalog only, it hosts no
files (ComicVine is to Mylar3 what TheTVDB is to Sonarr).

## Why the NAS (not mini/rig)

The output tree `/volume1/comics` is a **plain, non-SMB directory** (unlike the read-18 manga
share, which is a dedicated DSM shared folder the rig can CIFS-mount). The mini/rig can't cleanly
mount `/volume1/comics` as a write target, so Mylar3 must run **co-located on the NAS**. Output
lands in `/comics/Comics` (= `/volume1/comics/Comics`), exactly where Komga's Comics library scans.

## Ownership / uid

Runs as **PUID=1026 / PGID=100** (`btabaska:users`) — the same uid as Komga, so grabbed CBZ files
stay readable and NAS ACLs hold. Files written by any other uid would break Komga + the ACLs.

## ComicVine key (the one external credential)

Mylar3's LSIO image has **no ComicVine env var**, so the key is stored in
`/volume1/docker/mylar3/config/mylar/config.ini` under `[General] comicvine_api`. The real value
lives ONLY in the vault at `comicvine.api_key` (read-20); it never lands in the repo, compose, or
`.env`. `.env.example` documents the name for out-of-band restore. To re-apply after a wipe: stop
the container, write the vault value into `comicvine_api`, restart.

Comic Location (`destination_dir`) = `/comics/Comics`.

## Acquisition design (DDL-first)

- **read-22 (DONE)** — the built-in **GetComics DDL** provider is the PRIMARY path (plain HTTPS
  from the NAS, no indexer, no download client, no seedbox). Settings below.
- **read-23** — add Prowlarr (Full Sync, comics-category only) + off-site Betty Deluge over
  Tailscale as the **best-effort fallback** for titles GetComics doesn't carry.
- **read-24 / read-25** — consumer-end monitoring + wiki/Homepage surfacing.

## GetComics DDL settings (read-22)

Applied live in `config.ini` (not repo-mirrored — the file holds the ComicVine key + the API
key). Re-apply after a config wipe by stopping the container, setting these, and restarting
(Mylar rewrites `config.ini` on graceful shutdown, so edit the file **only while stopped**):

| section | key | value | why |
|---------|-----|-------|-----|
| `[DDL]` | `enable_ddl` | `True` | turn on the DDL engine |
| `[DDL]` | `enable_getcomics` | `True` | GetComics is the DDL source |
| `[DDL]` | `ddl_location` | `/comics/.mylar_ddl` | incoming/unpack dir — **same volume** as the library (fast rename on PP), hidden + outside `Comics/` so Komga ignores it; owned 1026:100 |
| `[Metatagging]` | `enable_meta` | `True` | writes `ComicInfo.xml` (bundled ComicTagger 1.3.5) + converts CBR→CBZ (unrar at `/usr/bin/unrar`) |
| `[General]` | `rename_files` | `True` | rename grabs to `file_format` → clean, Komga-parseable names |
| `[API]` | `api_enabled` | `True` | drives add/grab + the read-24 monitoring probe |
| `[API]` | `api_key` | *(vault `mylar3.api_key`)* | 32-hex; value lives only in the vault + `config.ini` |

Filing (unchanged from read-21, already Komga-ready): `folder_format = $Series ($Year)`,
`file_format = $Series $Annual $Issue ($Year)` → `Comics/Watchmen (1986)/Watchmen 1 (1986).cbz`.

**API cheatsheet** (`http://<nas>:8090/api?apikey=<key>&cmd=…`): `findComic&name=` → CV search;
`addComic&id=<comicvineid>` → add series; `getComic&id=<comicvineid>` → issue list w/ IssueIDs;
`queueIssue&id=<issueid>` → set Wanted + search (fires DDL); `getWanted` / `getHistory` → monitor.

**GetComics packs:** a single-issue want often matches a *complete-series pack* (e.g. Watchmen #1
matched the "Watchmen #1 – 12" 605 MB pack). Mylar unzips the pack and post-processes every issue
it owns — expect the whole run to land, not just the one issue. Pitfall: GetComics is a single
upstream — expect occasional misses (that's the read-23 fallback). ComicVine ~200 req/hr — pace
series adds/refreshes.

**Consumer proof (read-22, 2026-07-27):** added Watchmen (1986, CVID 3622) → queued #1 → GetComics
DDL grab → 12 CBZ filed under `Comics/Watchmen (1986)/` owned 1026:100 (valid CBZ, ComicInfo.xml) →
Komga scan: Comics series 1→2, all 12 books READY, page-1 streams HTTP 200 `image/jpeg`. No torrent.

## Deploy / upgrade

```sh
# first deploy / after a compose edit
ssh -t nas 'cd /volume1/docker/mylar3 && sudo /usr/local/bin/docker compose up -d'
# upgrade: bump the tag+digest in docker-compose.yml, then
ssh -t nas 'cd /volume1/docker/mylar3 && sudo /usr/local/bin/docker compose pull && sudo /usr/local/bin/docker compose up -d'
```

The NAS SSH user has no docker socket and no passwordless sudo — pipe the vault
`sudo.nas_password` into `sudo -S` and use the full `/usr/local/bin/docker` path.

Image is **digest-pinned** (`lscr.io/linuxserver/mylar3@sha256:4e105bb0…`, pulled on the NAS
2026-07-27) per the fix-38/I68 supply-chain posture.

## URLs

- Web UI / reverse proxy: **https://mylar.tabaska.us** (Caddy on the mini → `{$NAS_IP}:8090`)
- Direct: `http://192.168.10.4:8090`
