# Stash on the NAS

> Deploy and layout reference for the Stash media organizer running on the Synology DS920+ NAS, reusing the pre-existing `/volume1/stash` library.

_Source: `foss-setup/configs/nas/stash/README.md` · migrated + validated 2026-07-14_

[Stash](https://github.com/stashapp/stash) media organizer runs as a Docker container on the NAS (DS920+). It reuses the existing library at `/volume1/stash` from a prior install.

!!! note "Validated against live nas (2026-07-14)"
    `stash` appears in NAS `docker ps`: image `stashapp/stash:v0.31.1`, `Up 3 days`, port mapping `0.0.0.0:9999->9999/tcp`. HTTP probe `curl -sk http://192.168.10.4:9999/` returned `200`. Compose file on the NAS confirmed at `/volume1/docker/stash/` and pins the same `v0.31.1` tag.

## Layout

| Host path | Container path | Purpose |
|-----------|----------------|---------|
| `/volume1/stash/root` | `/data` | Media library (~915 GB) |
| `/volume1/stash/generated` | `/generated` | Screenshots, thumbnails, previews |
| `/volume1/stash/blobs` | `/blobs` | Cover art (and image blobs) |
| `/volume1/stash/cache` | `/cache` | Transcode / temp cache |
| `/volume1/stash/metadata` | `/metadata` | SQLite DB (created on first run) |
| `/volume1/docker/stash/config` | `/root/.stash` | Config, scrapers, plugins |

**Note:** No SQLite database was found in the old tree — tags/performers from the prior install are likely gone, but media files and generated thumbnails remain. After first launch, run **Settings → Tasks → Scan** to re-index `/data`.

!!! note "Validated against live nas (2026-07-14)"
    `/volume1/stash/` on the NAS contains `root`, `generated`, `blobs`, `cache`, and `metadata` subdirs as documented (all owned `btabaska:users`, mode `drwxrwx---`). The `metadata/` dir now exists (created since the source doc's "no SQLite found" note; created on first run). `root/` is the large media dir. Also present alongside: a Synology `@eaDir` thumbnail dir and `#recycle`.

## Compose file

Lives at `/volume1/docker/stash/` (deployed via Synology Container Manager / Docker Compose). Uses env-var substitution for paths and port:

```yaml
name: stash

services:
  stash:
    image: stashapp/stash:v0.31.1
    container_name: stash
    restart: always
    ports:
      - "${STASH_PORT:-9999}:9999"
    environment:
      - STASH_STASH=/data/
      - STASH_GENERATED=/generated/
      - STASH_METADATA=/metadata/
      - STASH_CACHE=/cache/
      - STASH_PORT=9999
      - TZ=${TZ:-America/New_York}
    volumes:
      - /etc/localtime:/etc/localtime:ro
      # Config, scrapers, plugins (new docker-side config dir)
      - ${CONFIG_DIR}:/root/.stash
      # Existing library from the prior install
      - ${STASH_ROOT}/root:/data
      - ${STASH_ROOT}/metadata:/metadata
      - ${STASH_ROOT}/cache:/cache
      - ${STASH_ROOT}/blobs:/blobs
      - ${STASH_ROOT}/generated:/generated
    logging:
      driver: json-file
      options:
        max-file: "5"
        max-size: "10m"
```

Env vars consumed at deploy time: `STASH_ROOT` (→ `/volume1/stash`), `CONFIG_DIR` (→ `/volume1/docker/stash/config`), `STASH_PORT` (default `9999`), `TZ` (default `America/New_York`).

Upstream references: https://github.com/stashapp/stash · docs https://docs.stashapp.cc/installation/docker/ · reference compose https://github.com/stashapp/stash/blob/develop/docker/production/docker-compose.yml

## Deploy

From your MacBook (sudo password required on the NAS):

```bash
ssh -t nas 'cd /volume1/docker/stash && sudo /usr/local/bin/docker compose pull && sudo /usr/local/bin/docker compose up -d'
```

Verify:

```bash
ssh -t nas 'sudo /usr/local/bin/docker ps --filter name=stash'
curl -sk -o /dev/null -w "%{http_code}\n" http://192.168.10.4:9999/
```

HTTPS (after Caddy on mini is updated): **https://stash.tabaska.us** (LAN / Tailscale only).

## Upgrade

Bump the image tag in the compose file (currently `v0.31.1`), read the release notes at https://github.com/stashapp/stash/releases, then:

```bash
ssh -t nas 'cd /volume1/docker/stash && sudo /usr/local/bin/docker compose pull && sudo /usr/local/bin/docker compose up -d'
```

---

[← NAS reference](index.md)
