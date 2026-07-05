# Stash on the NAS (DS920+)

[Stash](https://github.com/stashapp/stash) media organizer — reuses the existing library at `/volume1/stash` from a prior install.

## Layout

| Host path | Container path | Purpose |
|-----------|----------------|---------|
| `/volume1/stash/root` | `/data` | Media library (~915 GB) |
| `/volume1/stash/generated` | `/generated` | Screenshots, thumbnails, previews |
| `/volume1/stash/blobs` | `/blobs` | Cover art |
| `/volume1/stash/cache` | `/cache` | Transcode cache |
| `/volume1/stash/metadata` | `/metadata` | SQLite DB (created on first run) |
| `/volume1/docker/stash/config` | `/root/.stash` | Config, scrapers, plugins |

**Note:** No SQLite database was found in the old tree — tags/performers from the prior install are likely gone, but media files and generated thumbnails remain. After first launch, run **Settings → Tasks → Scan** to re-index `/data`.

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

Bump the image tag in `docker-compose.yml` (currently `v0.31.1`), read [release notes](https://github.com/stashapp/stash/releases), then:

```bash
ssh -t nas 'cd /volume1/docker/stash && sudo /usr/local/bin/docker compose pull && sudo /usr/local/bin/docker compose up -d'
```
