#!/bin/bash
# import-roms-v3.sh — copy the remaining PixelCove game sets from the seedbox
# into the NAS RomM library, so they exist on the NAS BEFORE the seedbox
# torrents are removed (2026-08-11, operator request). COPY ONLY — seedbox
# payloads keep seeding untouched; removal happens only after verify.
#
# Deferred (NOT copied here): the two "Sony PlayStation 3 (USA)" sets and the
# "Redump - Sony - PlayStation (America)" set are in Deluge Error state
# (incomplete downloads) — importing partial data would produce broken games.
# Complete those first, then import.
#
# 2026-08-11 21:45 (resume session): first run was SIGTERMed at 13:54:39 —
# collateral of the seedbox rclone-mount remount cycle (pkill rclone) — while
# mid-PS2_Part4. Re-run is safe (rclone copy skips transferred files). The
# "Bios collection Playstation 1" and "gog_games_s" legs are DISABLED below:
# both sources vanished from the seedbox between authoring and resume
# (presumably deleted in the same-day Deluge torrent cleanup) and never
# reached the NAS — re-source them if still wanted.
set -uo pipefail
RSRC="seedbox:/home/hd34/btabaska/files"
GAMES=/volume1/games
ROMS="$GAMES/romm/roms"
LOG="$GAMES/.rom-import/import-v3.log"
STATUS="$GAMES/.rom-import/STATUS-v3"
RC="/usr/local/bin/rclone --config /root/.config/rclone/rclone.conf --transfers 8 --checkers 16 --stats 5m --stats-one-line -v"
FAILS=0
LOG_TS() { printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }
run() { local lbl="$1"; shift; LOG_TS "-> $lbl"; "$@" >>"$LOG" 2>&1 || { LOG_TS "!! FAILED: $lbl (rc=$?)"; FAILS=$((FAILS+1)); }; }

mkdir -p "$(dirname "$LOG")" "$ROMS/saturn" "$ROMS/dc" "$GAMES/gog" "$GAMES/Strategy Guides" "$GAMES/romm/bios/psx"
echo "RUNNING $(date '+%F %T')" > "$STATUS"
LOG_TS "=== import-v3 start ==="

# --- PlayStation 2 (5 parts -> one ps2 folder) ---
for i in 1 2 3 4 5; do
  run "ps2: PS2_Part$i" $RC copy "$RSRC/PS2_Part$i" "$ROMS/ps2"
done

# --- Sega Saturn / Dreamcast (new platform folders) ---
run "saturn: Redump Saturn"      $RC copy "$RSRC/Redump - Sega - Saturn (2026-06-29)"   "$ROMS/saturn"
run "dc: Redump Dreamcast"       $RC copy "$RSRC/Redump - Sega - Dreamcast (2026-05-31)" "$ROMS/dc"

# --- WiiWare -> wii ---
run "wii: WiiWare"               $RC copy "$RSRC/WiiWare"        "$ROMS/wii"
run "wii: Japan.Wiiware"         $RC copy "$RSRC/Japan.Wiiware"  "$ROMS/wii"

# --- PS1 BIOS --- DISABLED 2026-08-11 21:45: source gone from seedbox (see header)
# run "bios: PS1 BIOS collection"  $RC copy "$RSRC/Bios collection Playstation 1" "$GAMES/romm/bios/psx"

# --- Non-console game content (kept under /Games, outside RomM roms) ---
# DISABLED 2026-08-11 21:45: gog_games_s gone from seedbox (see header)
# run "gog: GOG PC games"          $RC copy "$RSRC/gog_games_s"    "$GAMES/gog"
run "guides: Strategy Guides"    $RC copy "$RSRC/Strategy Guides" "$GAMES/Strategy Guides"

LOG_TS "normalizing ownership to 1026:100"
chown -R 1026:100 "$ROMS/ps2" "$ROMS/saturn" "$ROMS/dc" "$ROMS/wii" "$GAMES/gog" "$GAMES/Strategy Guides" "$GAMES/romm/bios/psx" 2>>"$LOG"

LOG_TS "=== summary (NAS-side sizes) ==="
for p in "ps2:$ROMS/ps2" "saturn:$ROMS/saturn" "dc:$ROMS/dc" "wii:$ROMS/wii" "gog:$GAMES/gog" "guides:$GAMES/Strategy Guides" "ps1bios:$GAMES/romm/bios/psx"; do
  name="${p%%:*}"; path="${p#*:}"
  LOG_TS "$name: $(find "$path" -type f 2>/dev/null | wc -l) files, $(du -sh "$path" 2>/dev/null | cut -f1)"
done
LOG_TS "failures: $FAILS"
[ "$FAILS" -eq 0 ] && echo "DONE-OK $(date '+%F %T')" > "$STATUS" || echo "DONE-WITH-FAILURES=$FAILS $(date '+%F %T')" > "$STATUS"
LOG_TS "=== import-v3 end (failures=$FAILS) ==="
