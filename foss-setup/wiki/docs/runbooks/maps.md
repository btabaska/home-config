# Offline maps (PMTiles + Photon)

Runbook for the `maps-pmtiles-serve` and `maps-photon-geocode` verification checks and
general operation of the fleet's **offline maps** (lai-17, local-ai buildout).
Service page: [maps](../services/maps.md).

- **Host:** mini (Ubuntu Mac mini, `192.168.10.2`), Docker, stack `/opt/stacks/maps`
- **URLs:** <https://maps.tabaska.us> (viewer + tiles + geocode, via Caddy) · `http://192.168.10.2:8899` (go-pmtiles LAN direct) · `http://192.168.10.2:2322` (Photon LAN direct)
- **Compose:** live `/opt/stacks/maps/compose.yaml`; repo mirror `foss-setup/configs/docker-stack/stacks/maps/`
- **Images:** `ghcr.io/protomaps/go-pmtiles:v1.31.2` and `rtuszik/photon-docker:2.3.1` (both digest-pinned)
- **Viewer assets:** `/opt/stacks/caddy/site/maps/` (served by Caddy file_server; `index.html` + `style.json` tracked, `fonts/`+`sprites/`+`maplibre-gl.*` vendored/gitignored, re-fetch with `fetch-maps-assets.sh`)
- **Secrets:** none — public map data, LAN/tailnet-only, nothing forwarded outward

## Architecture

The Caddy vhost `maps.tabaska.us` fans out three ways:

- `/pmtiles/*` → `pmtiles:8080` (go-pmtiles `serve`). It reads `data/us.pmtiles` and exposes
  a TileJSON at `/pmtiles/us.json` and tiles at `/pmtiles/us/{z}/{x}/{y}.mvt`. The container
  is launched with `--public-url https://maps.tabaska.us/pmtiles` so the TileJSON advertises
  correct public URLs.
- `/geocode/*` → `photon:2322` (Photon US geocoder). `/geocode/api?q=<place>` returns GeoJSON.
- everything else → the static MapLibre viewer from `/srv/static/maps` (the caddy site dir).

**Why a dedicated go-pmtiles container** and not the Caddy pmtiles plugin: the fleet Caddy is a
custom build with only the Cloudflare-DNS module (`caddy list-modules | grep pmtiles` → empty).
Rebuilding the whole fleet Caddy to add a tile module is heavier and riskier than one small
pinned serve container behind a normal reverse-proxy vhost, so we do that.

## The US PMTiles extract

`data/us.pmtiles` (~18GB) is a **CONUS** cut (bbox `-125,24.5,-66.5,49.5`, zoom 0-15) taken from
the current **remote** Protomaps daily planet build (~137GB) via HTTP **range requests** — the
whole planet is never downloaded. Rebuild / refresh:

```
ssh mini /opt/stacks/maps/run-extract.sh     # writes data/us.pmtiles.tmp then atomically renames
tail -f /opt/stacks/maps/logs/extract.log
```

Edit the `BUILD=` date URL in `run-extract.sh` to pull a newer planet build (find current builds at
`maps.protomaps.com/builds`; the file pattern is `build.protomaps.com/YYYYMMDD.pmtiles`). Each extra
zoom level roughly doubles the archive size; z15 CONUS ≈ 18-19GB, z14 ≈ 9GB. After a re-extract the
running `pmtiles` container picks up the new file on its next request (bind mount, read-only).

## The Photon US index

On first boot Photon (`REGION=usa`) downloads a ~10GB index from `r2.koalasec.org` and imports it to
~17GB into the `maps_photon_data` volume. **The Java API only binds `:2322` after the import
completes** — so an empty geocode result / `mode=building` for the first hour is normal, not a
failure. Watch: `ssh mini 'docker logs --tail 20 photon'`. `UPDATE_STRATEGY=DISABLED` keeps it from
re-pulling 10GB every 30 days; to refresh manually, `docker compose up -d photon` after clearing the
volume (or flip `UPDATE_STRATEGY` and set `INITIAL_DOWNLOAD` appropriately).

## OSM MCP vs Photon (offline vs online)

The **offline** geocoder is Photon (this stack), consumed by the viewer's search box. The
**OpenStreetMap MCP** (`@cyanheads/openstreetmap-mcp-server`, wired into opencode's build/plan agents
in `local-ai-tooling`) is a separate, **online** tool that uses PUBLIC OSM Nominatim + Overpass —
Photon's API is not Nominatim-compatible, so it cannot be pointed at Photon. The OSM MCP is
**opencode-native only**: it is NOT bridged through mcpo (the pinned mcpo container ships Node 22,
below the server's required Node ≥24 → `EBADENGINE` → mcpo can't mount it) and NOT registered in
Open WebUI (the OWUI visible-tool budget stays 40/40).

## Verification checks

- **`maps-pmtiles-serve`** (`/opt/verification/bin/maps-pmtiles-serve.sh`, host mini): fetches the
  TileJSON through Caddy (asserts CONUS bounds + maxzoom) and a real US tile at `z8` over the central
  US, asserting valid **gzipped MVT** bytes. It sends `Accept-Encoding: gzip` so Caddy passes
  go-pmtiles' gzip straight through (magic `1f8b`) — the exact bytes MapLibre receives. Without that
  header Caddy transparently decompresses to raw protobuf, which is why the assert is header-pinned.
- **`maps-photon-geocode`** (`/opt/verification/bin/maps-photon-geocode.sh`, host mini): build-mode
  aware. CONTENT once the index lands — a real geocode of a US city must return coordinates inside
  CONUS. BUILDING before then — "container running but `:2322` not answering yet" is a PASS. A
  persistently crash-looping Photon is caught by `containers-health-mini`, not here.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Map blank / tiles 404 | `ssh mini 'ls -lh /opt/stacks/maps/data/us.pmtiles; curl -s localhost:8899/us.json'`. Missing / `.tmp` left → re-run `run-extract.sh`. Present but 404 via Caddy → check the `maps.tabaska.us` vhost `/pmtiles/*` route + reload Caddy. |
| Geocode empty for a long time | Photon still importing — `docker logs --tail 20 photon`. Normal on first boot (~an hour). |
| Missing labels/icons | Vendored fonts/sprites gone — `ssh mini /opt/stacks/maps/fetch-maps-assets.sh`, hard-refresh. |
| Tile bytes not gzip in a probe | curl decompresses when no `Accept-Encoding: gzip` header is sent; the browser and the check send it, so this is expected only for a bare curl. |
