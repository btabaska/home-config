#!/usr/bin/env bash
# lai-17 consumer end: prove the offline US map SERVES through the mini Caddy vhost
# maps.tabaska.us — not just that the container is up. Asserts the go-pmtiles TileJSON
# (CONUS bounds + maxzoom) AND fetches a REAL US vector tile, asserting valid gzipped
# MVT bytes. Browser-faithful: sends `Accept-Encoding: gzip` so Caddy passes the
# go-pmtiles gzip straight through (magic 1f8b) — exactly what MapLibre receives in the
# viewer. Green-but-broken modes this catches: empty/short tile (extract lost/partial),
# non-tile body (proxy misroute -> HTML), bounds/zoom drift (wrong archive swapped in).
set -u
R='--resolve maps.tabaska.us:443:127.0.0.1'
B='https://maps.tabaska.us'

meta=$(curl -s -m 15 $R "$B/pmtiles/us.json")
metaline=$(printf '%s' "$meta" | python3 -c '
import sys,json
try:
    d=json.load(sys.stdin)
    b=d.get("bounds",[0,0,0,0]); mz=d.get("maxzoom",0)
    ok = mz>=12 and b[0]<=-100 and b[2]>=-80 and b[1]<=30 and b[3]>=45
    print(("Y" if ok else "N"), mz, ",".join(str(x) for x in b))
except Exception:
    print("N 0 na")' 2>/dev/null)
metaok=$(printf '%s' "$metaline" | awk '{print $1}')
mz=$(printf '%s' "$metaline" | awk '{print $2}')
bounds=$(printf '%s' "$metaline" | awk '{print $3}')

# Real US tile: z8 over the central US (dense: land + water + roads). Browser-faithful.
tmp=$(mktemp)
code=$(curl -s -m 15 $R -H 'Accept-Encoding: gzip' -o "$tmp" -w '%{http_code}' "$B/pmtiles/us/8/65/95.mvt")
sz=$(wc -c < "$tmp" | tr -d ' ')
magic=$(od -An -tx1 -N2 "$tmp" | tr -d ' \n')
rm -f "$tmp"

if [ "$metaok" = Y ] && [ "$code" = 200 ] && [ "${sz:-0}" -gt 2000 ] && [ "$magic" = 1f8b ]; then
  echo "MAPS_PMTILES_OK maxzoom=$mz bounds=$bounds tile_bytes=$sz magic=$magic"
else
  echo "MAPS_PMTILES_BAD metaok=$metaok code=$code bytes=${sz:-0} magic=${magic:-none}"
fi
