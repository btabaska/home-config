#!/usr/bin/env bash
# Convert FLAC -> ALAC (Apple Lossless .m4a) IN PLACE under a music dir, for the
# stock-firmware iPod Classic (which can't play FLAC). On successful, verified
# conversion the source FLAC is DELETED. MP3/AAC are left untouched (iPod-native).
#
# iPod Classic ALAC limits: 16-bit, <=48 kHz. So: always output 16-bit; resample
# to 48 kHz only if the source is >48 kHz (hi-res). Tags + embedded cover art are
# carried across. Idempotent/resumable: skips a track whose .m4a already exists.
#
# SAFETY GATE: refuses to run unless the NAS master copy has been verified — the
# caller must create the sentinel file (see MIGRATION_OK below). This exists so the
# FLAC (deleted here) is never removed before its master copy is confirmed on the NAS.
#
# Usage:  MUSIC_DIR=~/Music ./flac-to-alac-inplace.sh          # dry-run (lists)
#         MUSIC_DIR=~/Music APPLY=1 ./flac-to-alac-inplace.sh  # convert + delete FLAC
set -uo pipefail

MUSIC_DIR="${MUSIC_DIR:-$HOME/Music}"
APPLY="${APPLY:-0}"
SENTINEL="${MIGRATION_OK:-$HOME/.music-migration-verified}"
LOG="$HOME/flac-to-alac.log"

if [[ ! -f "$SENTINEL" ]]; then
  echo "REFUSING TO RUN: safety sentinel '$SENTINEL' not present." >&2
  echo "Create it only AFTER the NAS master copy is verified complete." >&2
  exit 3
fi

echo "=== $(date -u) flac-to-alac start (APPLY=$APPLY, dir=$MUSIC_DIR) ===" | tee -a "$LOG"
total=0; converted=0; skipped=0; failed=0

while IFS= read -r -d '' flac; do
  total=$((total+1))
  out="${flac%.flac}.m4a"
  if [[ -f "$out" ]]; then skipped=$((skipped+1)); continue; fi
  if [[ "$APPLY" != "1" ]]; then echo "would convert: $flac"; continue; fi

  # decide resample: only if source rate > 48000
  rate=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of csv=p=0 "$flac" 2>/dev/null)
  arflag=(); [[ -n "$rate" && "$rate" -gt 48000 ]] 2>/dev/null && arflag=(-ar 48000)

  # temp MUST keep a .m4a extension — ffmpeg picks the muxer from the extension,
  # and a ".partial" suffix makes it fail with "Unable to find a suitable output format".
  tmp="${out%.m4a}.converting.m4a"
  if ffmpeg -nostdin -v error -i "$flac" \
        -map 0:a -map 0:v? -c:v copy -disposition:v:0 attached_pic \
        -c:a alac -sample_fmt s16p "${arflag[@]}" \
        -map_metadata 0 -movflags +faststart "$tmp" 2>>"$LOG"; then
    # verify the output has a decodable audio stream and sane size
    osz=$(stat -c%s "$tmp" 2>/dev/null || echo 0)
    if ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$tmp" 2>/dev/null | grep -q alac && [[ "$osz" -gt 100000 ]]; then
      mv "$tmp" "$out"
      rm -f "$flac"
      converted=$((converted+1))
      echo "OK  $flac -> $(basename "$out")" >> "$LOG"
    else
      rm -f "$tmp"; failed=$((failed+1)); echo "VERIFY-FAIL (kept FLAC): $flac" | tee -a "$LOG"
    fi
  else
    rm -f "$tmp"; failed=$((failed+1)); echo "FFMPEG-FAIL (kept FLAC): $flac" | tee -a "$LOG"
  fi
done < <(find "$MUSIC_DIR" -type f -iname '*.flac' -print0)

echo "=== done: total=$total converted=$converted skipped=$skipped failed=$failed ===" | tee -a "$LOG"
