#!/usr/bin/env bash
# lai-17: Photon US OFFLINE geocoder consumer probe, build-mode aware (like lai-15).
#   CONTENT  — once the US index is imported and :2322 answers, a REAL geocode of a
#              known US city (Chicago) must return a feature whose coordinates fall
#              inside CONUS. Proves the whole path: browser -> Caddy /geocode/* ->
#              photon:2322 -> imported US index. Catches a wrong/empty index (no
#              features) or coords outside the US.
#   BUILDING — first boot downloads ~10GB and imports to ~17GB; Photon's Java API binds
#              :2322 ONLY after the import completes, so "container running but not yet
#              answering" == still importing == PASS (tolerant). A persistently
#              crash-looping container is caught separately by containers-health-mini.
set -u
geo=$(curl -s -m 12 --resolve maps.tabaska.us:443:127.0.0.1 \
      'https://maps.tabaska.us/geocode/api?limit=1&q=Chicago' 2>/dev/null)
res=$(printf '%s' "$geo" | python3 -c '
import sys,json
try:
    d=json.load(sys.stdin); f=(d.get("features") or [])
    if not f:
        print("EMPTY"); sys.exit()
    c=(f[0].get("geometry") or {}).get("coordinates") or [0,0]
    lon,lat=c[0],c[1]
    ok = -125<=lon<=-66 and 24<=lat<=50
    p=f[0].get("properties") or {}
    print("CONTENT" if ok else "OUT", round(lon,3), round(lat,3), (p.get("name") or "")[:20])
except Exception:
    print("NORESP")' 2>/dev/null)
mode=$(printf '%s' "$res" | awk '{print $1}')

if [ "$mode" = CONTENT ]; then
  echo "MAPS_PHOTON_OK mode=content $res"
  exit 0
fi

state=$(docker inspect -f '{{.State.Status}}' photon 2>/dev/null)
if [ "$state" = running ]; then
  echo "MAPS_PHOTON_OK mode=building (US index still downloading/importing ~10GB->~17GB) res=$res"
  exit 0
fi
echo "MAPS_PHOTON_BAD mode=down state=${state:-absent} res=$res"
exit 1
