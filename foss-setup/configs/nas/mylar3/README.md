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

Configured in later tasks — this task is base install + first-run config only:

- **read-22** — enable the built-in **GetComics DDL** provider (plain HTTPS from the NAS, no
  indexer, no download client). This is the PRIMARY path.
- **read-23** — add Prowlarr (Full Sync, comics-category only) + off-site Betty Deluge over
  Tailscale as the **best-effort fallback** for titles GetComics doesn't carry.
- **read-24 / read-25** — consumer-end monitoring + wiki/Homepage surfacing.

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
