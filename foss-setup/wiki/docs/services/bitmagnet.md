# bitmagnet

Bitmagnet — self-hosted BitTorrent DHT crawler + metadata index (seed-12)

| | |
|---|---|
| **Host** | [nas](../hosts/nas.md) |
| **URL** | https://bitmagnet.tabaska.us |
| **Source** | `foss-setup/configs/nas/bitmagnet/docker-compose.yml` |
| **Notes** | Self-hosted DHT crawler + local Torznab indexer for Prowlarr (rate-limit-proof hedge). |
| **Upstream docs** | <http://192.168.10.4:3333/torznab> |

## About

Bitmagnet is a self-hosted BitTorrent DHT crawler + metadata index that acts as a LOCAL Torznab indexer for Prowlarr and the *arr stack — an indexer-redundancy hedge (seed-12). It runs on the NAS (Synology DS920+, `192.168.10.4`) via DSM Container Manager / Docker Compose (project `bitmagnet`), reachable at https://bitmagnet.tabaska.us (LAN `http://192.168.10.4:3333`). WHY it exists: the public indexers the arrs rely on are rate-limited and fragile — IPTorrents caps at roughly 600 grabs/day, EZTV/The Pirate Bay throttle and periodically go dark — so if they choke, Prowlarr is left without a source. Bitmagnet answers that by continuously crawling the public BitTorrent DHT and harvesting torrent **metadata only** (infohash + name + file list + size); it has no query cap, no Cloudflare challenge, and — because it is an INDEX, not a download client — it never downloads or seeds torrent CONTENT (that is its designed function, and the reason it is safe to run 24/7). It lives on the NAS co-located with Prowlarr and the arrs so the Torznab hop is a LAN request. The stack is two containers: `bitmagnet` (image `ghcr.io/bitmagnet-io/bitmagnet:latest` digest-pinned `@sha256:cf2c16fa…`, supply-chain posture, pulled on the NAS 2026-07-28), launched as `worker run --all` so it runs the DHT crawler + the queue/classifier + the HTTP/Torznab/GraphQL server together; and `bitmagnet-postgres` (image `postgres:16-alpine` digest-pinned `@sha256:57c72fd2…`, `shm_size: 1g`, `shared_buffers=256MB`) — Bitmagnet REQUIRES Postgres, SQLite is not supported. The DB is container-only (NOT published) with its password in `/volume1/docker/bitmagnet/.env` (`POSTGRES_PASSWORD`, vault `bitmagnet.postgres_password`); its data lives on a writable bind mount at `/volume1/docker/bitmagnet/postgres`. Ports: `3333` serves the web UI + `/torznab` + `/graphql`; `3334` (TCP+UDP) is the DHT node, published so the crawler pulls inbound DHT peers and ingests faster. No TMDB API key is configured, so content classification (movie/tv enrichment) is skipped — but Torznab keyword search works on the raw torrent-name index without it (adding `TMDB_API_KEY` later would enrich results). Wiring into Prowlarr: added as a **Generic Torznab** indexer named `Bitmagnet (DHT)` — URL `http://192.168.10.4:3333/torznab`, API Path `/api`, API Key = any non-empty value (Bitmagnet does not authenticate Torznab, but Prowlarr's form requires a value; vault `bitmagnet.torznab_apikey`). Access is LAN/tailnet-only through the mini's Caddy (`reverse_proxy {$NAS_IP}:3333`, `import local_tls`, Let's Encrypt via Cloudflare DNS-01). Content — not liveness — is watched by TWO consumer-end verification checks (both `warn`): `bitmagnet-dht-ingesting` asserts the crawler wrote NEW torrents to its Postgres in the last 30 minutes (a dead crawler = a frozen, useless index), and `bitmagnet-torznab-via-prowlarr` finds the `Bitmagnet (DHT)` indexer in Prowlarr by name and runs a real keyword search THROUGH Prowlarr scoped to it, requiring > 0 real hits — proving the whole chain (registered + Torznab reachable + returns torrents) in one shot. At deploy the pipeline was proven end-to-end: within minutes the DHT crawler ingested thousands of torrents (0 → 1128+ and climbing), 232 were classified into searchable content, a `1080p` Torznab query returned real titles with magnet links, and the Prowlarr indexer test passed with a scoped search returning 5 real results.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `bitmagnet` | `ghcr.io/bitmagnet-io/bitmagnet:latest@sha256:cf2c16fac5b51f1c18e630b4710175d35d7e44b83012cfd05a2b43712feec05e` | `3333:3333`, `3334:3334/tcp`, `3334:3334/udp` |
| `postgres` | `postgres:16-alpine@sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777` | — |

## Volumes

| Service | Volume |
|---|---|
| `postgres` | `/volume1/docker/bitmagnet/postgres:/var/lib/postgresql/data` |

## Troubleshooting

- **Prowlarr's Bitmagnet indexer tests OK but searches return zero results** — Bitmagnet's Torznab searches its CLASSIFIED content, which lags DHT discovery — right after deploy the raw `torrents` table fills fast but `torrent_contents` (what Torznab reads) trails while the classifier processes the queue. Give it a few minutes and re-test. Confirm ingestion + classification are both moving: `ssh nas` then `sudo /usr/local/bin/docker exec bitmagnet-postgres psql -U postgres -d bitmagnet -tAc 'SELECT count(*) FROM torrents; SELECT count(*) FROM torrent_contents;'` — both should climb. A raw check that bypasses classification: `curl -s 'http://192.168.10.4:3333/torznab/api?t=search&q=1080p' | grep -c '<item>'`.
- **The DHT crawler is not ingesting — `torrents` row count is flat / `bitmagnet-dht-ingesting` fails** — Check the crawler actually started: `sudo /usr/local/bin/docker logs --tail 30 bitmagnet` should show `started worker {"key": "dht_crawler"}` with no panics. The crawler needs UDP reachability for the DHT — confirm port `3334/udp` is published (`docker ps` shows `3334->3334/udp`) and not blocked. A fresh container spends the first ~30s running Goose migrations before the workers start; wait past that. If it truly ingests nothing, restart the stack: `cd /volume1/docker/bitmagnet && sudo /usr/local/bin/docker compose restart bitmagnet`.
- **`bitmagnet-postgres` container will not start — "Bind mount failed: /volume1/docker/bitmagnet/postgres does not exist"** — Docker on Synology does NOT auto-create bind-mount source directories. Create it first: `sudo mkdir -p /volume1/docker/bitmagnet/postgres` then `cd /volume1/docker/bitmagnet && sudo /usr/local/bin/docker compose up -d`. The Postgres image chowns the directory to its own uid on first init, so no manual ownership is needed.

## Operations

```bash
# NAS stack — manage via DSM Container Manager (project: bitmagnet)
# or over SSH (sudo required): cd /volume1/docker/bitmagnet && sudo docker compose ps
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
