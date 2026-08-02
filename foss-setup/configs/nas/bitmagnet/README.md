# Bitmagnet (NAS) — deploy + indexer posture

Self-hosted BitTorrent DHT crawler + metadata index acting as a **local Torznab
indexer** for Prowlarr and the *arr stack (indexer-redundancy hedge, seed-12).
Runs on the NAS (`192.168.10.4`) via DSM Container Manager / Docker Compose,
project `bitmagnet`. Two containers: `bitmagnet` (crawler + classifier +
HTTP/Torznab/GraphQL) and `bitmagnet-postgres` (required — SQLite unsupported).

- Compose: [`docker-compose.yml`](./docker-compose.yml) — the source of truth for
  the containers. Postgres password in `/volume1/docker/bitmagnet/.env`
  (`POSTGRES_PASSWORD`, vault `bitmagnet.postgres_password`).
- Ports: `3333` = web UI + `/torznab` + `/graphql`; `3334/tcp+udp` = DHT node.
- Web/Torznab: `http://192.168.10.4:3333`, `https://bitmagnet.tabaska.us` (LAN/tailnet).

## Prowlarr indexer posture — DEMOTED to interactive-only (fix-50, 2026-08-02)

> This setting lives in **prowlarr.db** (`/volume1/docker/prowlarr/config/prowlarr.db`),
> NOT in any compose/env file, so it is documented here authoritatively. A Prowlarr
> rebuild / DB restore that predates 2026-08-02 will re-enable auto-grab and MUST be
> re-demoted using the steps below.

**Why:** a DHT crawler indexes whatever the swarm carries — dominated by low-quality
re-encodes and foreign-audio (Russian/Bulgarian/Korean) dub rips. With RSS + Automatic
Search enabled, radarr auto-grabbed junk ~hourly and sonarr ~every 30 min, importing
dubbed copies of already-owned titles into the movie library and stalling the arr
queues (fleet-sweep-2026-08-02 finding **SC2**; timeouts **SM6/SM27**). Bitmagnet is a
fine *manual* fallback for throttle days, but a terrible *automatic* grab source.

**Posture:** Bitmagnet participates in **manual/interactive search only**. Implemented
with a dedicated Prowlarr **App Sync Profile** (a.k.a. "Sync Profile") so the demotion
propagates to every arr on full-sync and survives re-syncs:

- Prowlarr → Settings → Apps → **Sync Profiles** → profile **`Interactive-Only (fix-50)`**
  - Enable RSS: **OFF** (`enableRss=false`)
  - Enable Automatic Search: **OFF** (`enableAutomaticSearch=false`)
  - Enable Interactive Search: **ON** (`enableInteractiveSearch=true`)
  - Minimum Seeders: `1`
- Prowlarr → Indexers → **`Bitmagnet (DHT)`** → Sync Profile = `Interactive-Only (fix-50)`.
- After assigning, Prowlarr syncs to the arrs; radarr/sonarr Bitmagnet indexer then shows
  **Enable RSS off / Enable Automatic Search off / Enable Interactive Search on**.
- All OTHER indexers stay on the `Standard` profile (RSS/auto/interactive all on).

### Reproduce via API (Prowlarr `:9696`, key = `<ApiKey>` from `config.xml`)

```sh
# 1. create the interactive-only sync profile (idempotent — skip if it exists)
curl -s -X POST -H "X-Api-Key: $PK" -H 'Content-Type: application/json' \
  http://192.168.10.4:9696/api/v1/appprofile \
  -d '{"name":"Interactive-Only (fix-50)","enableRss":false,"enableAutomaticSearch":false,"enableInteractiveSearch":true,"minimumSeeders":1}'
# 2. point the Bitmagnet indexer at it (GET the object, set appProfileId, PUT it back;
#    the masked "********" apiKey field is preserved by Prowlarr on PUT)
#    then force a sync:
curl -s -X POST -H "X-Api-Key: $PK" -H 'Content-Type: application/json' \
  http://192.168.10.4:9696/api/v1/command -d '{"name":"ApplicationIndexerSync"}'
```

### Verify

```
python3 /opt/verification/bin/arr-grab-indexer-share.py demoted
# expect: DEMOTED_OK radarr=rss:F/auto:F sonarr=rss:F/auto:F
```

Guarded by verification checks in `foss-setup/verification/checks.d/media-indexers.yaml`:
`bitmagnet-demoted-interactive-only` (regression) and `arr-grab-source-not-storming`
(class) — plus `bitmagnet-dht-ingesting` and the time-boxed `bitmagnet-torznab-via-prowlarr`.
