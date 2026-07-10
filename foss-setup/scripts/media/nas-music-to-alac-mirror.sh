#!/usr/bin/env bash
# Maintain ~/Music on the rig as an iPod-playable MIRROR of the NAS master library.
#   NAS /volume1/music (FLAC + MP3/AAC, read-only mount)  ->  ~/Music
#   FLAC  -> ALAC (.m4a, 16-bit, <=48kHz)   [iPod Classic can't play FLAC/hi-res]
#   MP3/AAC/M4A -> copied verbatim           [already iPod-native]
# Incremental (skips up-to-date targets), prunes orphans (tracks removed from NAS).
# Read-only on the NAS; only ever writes/deletes under ~/Music.
#
# SAFETY: if the NAS source looks empty/unavailable, ABORT before pruning — a NAS
# blip must never wipe the mirror.
set -uo pipefail

SRC="${SRC:-/mnt/nas-music-ro}"
DST="${DST:-$HOME/Music}"
LOG="${LOG:-$HOME/nas-alac-mirror.log}"
LOCK="$HOME/.nas-alac-mirror.lock"

exec >>"$LOG" 2>&1
exec 9>"$LOCK"; flock -n 9 || { echo "$(date -Is) already running, skip"; exit 0; }
echo "=== $(date -Is) mirror start ==="

ls "$SRC" >/dev/null 2>&1   # trigger the automount
# safety gate: source must look populated, else abort (don't prune on a dead mount)
srcflac=$(find "$SRC" -iname '*.flac' -not -path '*/#recycle/*' -not -path '*/@eaDir/*' 2>/dev/null | head -400 | wc -l)
if [ "$srcflac" -lt 20 ]; then
  echo "SOURCE looks empty/unavailable (flac<20). Aborting to protect the mirror."; exit 1
fi

mkdir -p "$DST"
conv=0; copied=0; skip=0; fail=0

# 1) mirror NAS -> ~/Music
while IFS= read -r -d '' f; do
  rel="${f#"$SRC"/}"
  ext="${f##*.}"; ext="${ext,,}"
  if [ "$ext" = "flac" ]; then
    out="$DST/${rel%.*}.m4a"
    if [ -f "$out" ] && [ "$out" -nt "$f" ]; then skip=$((skip+1)); continue; fi
    mkdir -p "$(dirname "$out")"
    rate=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of csv=p=0 "$f" 2>/dev/null)
    ar=(); [ "${rate:-0}" -gt 48000 ] 2>/dev/null && ar=(-ar 48000)
    tmp="${out%.m4a}.converting.m4a"
    if ffmpeg -y -nostdin -v error -i "$f" -map 0:a -map 0:v? -c:v copy -disposition:v:0 attached_pic \
         -c:a alac -sample_fmt s16p "${ar[@]}" -map_metadata 0 -movflags +faststart "$tmp" 2>>"$LOG" \
       && ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$tmp" 2>/dev/null | grep -q alac; then
      mv -f "$tmp" "$out"; conv=$((conv+1))
    else rm -f "$tmp"; fail=$((fail+1)); echo "FAIL transcode: $rel"; fi
  else
    out="$DST/$rel"
    if [ -f "$out" ] && [ ! "$f" -nt "$out" ]; then skip=$((skip+1)); continue; fi
    mkdir -p "$(dirname "$out")"
    cp -p "$f" "$out" && copied=$((copied+1)) || { fail=$((fail+1)); echo "FAIL copy: $rel"; }
  fi
done < <(find "$SRC" -type f \( -iname '*.flac' -o -iname '*.mp3' -o -iname '*.m4a' -o -iname '*.aac' \) \
           -not -path '*/#recycle/*' -not -path '*/@eaDir/*' -print0)

# 2) prune orphans: ~/Music files whose NAS source no longer exists
pruned=0
while IFS= read -r -d '' d; do
  rel="${d#"$DST"/}"; base="${rel%.*}"
  if [ -f "$SRC/$rel" ] || [ -f "$SRC/$base.flac" ] || [ -f "$SRC/$base.m4a" ] || [ -f "$SRC/$base.aac" ] || [ -f "$SRC/$base.mp3" ]; then continue; fi
  rm -f "$d"; pruned=$((pruned+1)); echo "pruned orphan: $rel"
done < <(find "$DST" -type f \( -iname '*.m4a' -o -iname '*.mp3' -o -iname '*.aac' \) -print0)
find "$DST" -type d -empty -delete 2>/dev/null

echo "=== $(date -Is) done: converted=$conv copied=$copied skipped=$skip failed=$fail pruned=$pruned ==="
