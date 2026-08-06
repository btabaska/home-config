#!/usr/bin/env bash
# lai-17: extract a CONUS region from the remote Protomaps daily planet build via
# range requests (no full 137GB download). Atomic: write .tmp then rename.
set -euo pipefail
BUILD="https://build.protomaps.com/20260806.pmtiles"
BBOX="-125,24.5,-66.5,49.5"   # CONUS (contiguous US)
IMG="ghcr.io/protomaps/go-pmtiles:v1.31.2"
cd /opt/stacks/maps/data
echo "[extract] start $(date -u +%FT%TZ) build=$BUILD bbox=$BBOX maxzoom=15"
docker run --rm -v /opt/stacks/maps/data:/data "$IMG" extract "$BUILD" /data/us.pmtiles.tmp \
  --bbox="$BBOX" --maxzoom=15 --download-threads=8
mv -f /opt/stacks/maps/data/us.pmtiles.tmp /opt/stacks/maps/data/us.pmtiles
echo "[extract] DONE $(date -u +%FT%TZ) size=$(du -h /opt/stacks/maps/data/us.pmtiles | cut -f1)"
