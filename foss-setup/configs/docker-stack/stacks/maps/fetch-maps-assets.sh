#!/usr/bin/env bash
# lai-17: fetch the STATIC map viewer assets (fonts glyph PBFs, sprites, maplibre-gl
# bundle) for maps.tabaska.us into the Caddy static site dir. These are vendored
# binary blobs (kept OUT of git — see .gitignore) so the offline map viewer renders
# labels + icons + geometry with NO external CDN at runtime. Re-run to rebuild.
set -euo pipefail
DEST="/opt/stacks/caddy/site/maps"
ASSETS="https://raw.githubusercontent.com/protomaps/basemaps-assets/main"
MAPLIBRE_VERSION="5.6.1"
RANGES="0-255 256-511 512-767 768-1023 8192-8447 8448-8703"
FONTSTACKS=("Noto Sans Regular" "Noto Sans Medium" "Noto Sans Italic")

mkdir -p "$DEST/sprites" "$DEST/fonts"
# Fonts (Latin + diacritics + punctuation ranges — enough for US English labels)
for fs in "${FONTSTACKS[@]}"; do
  mkdir -p "$DEST/fonts/$fs"
  enc=$(printf %s "$fs" | sed "s/ /%20/g")
  for r in $RANGES; do
    curl -fsSL "$ASSETS/fonts/$enc/$r.pbf" -o "$DEST/fonts/$fs/$r.pbf"
  done
done
# Sprites (schema v4 light, 1x + 2x)
for s in light.json light.png light@2x.json light@2x.png; do
  curl -fsSL "$ASSETS/sprites/v4/$s" -o "$DEST/sprites/$s"
done
# MapLibre GL JS (pinned) — hosted locally for offline use
curl -fsSL "https://unpkg.com/maplibre-gl@${MAPLIBRE_VERSION}/dist/maplibre-gl.js" -o "$DEST/maplibre-gl.js"
curl -fsSL "https://unpkg.com/maplibre-gl@${MAPLIBRE_VERSION}/dist/maplibre-gl.css" -o "$DEST/maplibre-gl.css"
echo "assets fetched to $DEST"
