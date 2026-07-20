#!/bin/bash
# import-seedbox-roms.sh — copy the seedbox "manual" ROM collections into the
# RoMM library. Ran 2026-07-19/20 (repo copy is the provenance record; deployed
# ad-hoc to nas:/volume1/games/.rom-import/import.sh, launched as root via
# setsid nohup). Re-runnable: rclone copy skips already-transferred files, so a
# partial/failed run resumes safely. Copied ~790G in ~6h; see
# wiki services/romm for the resulting library state.
# Original header follows.
#
# copy the seedbox "manual" ROM collections into the RoMM
# library (2026-07-19, operator request). COPY ONLY — the seedbox payloads keep
# seeding untouched. v2: direct `rclone copy` (parallel transfers) instead of
# rsync-through-the-FUSE-mount — small-file sets crawled at ~30KB/s through the
# mount's serialized per-file SFTP round-trips. Runs as root (rclone conf is
# root's); ownership normalized to 1026:100 at the end. Region-sorted sets are
# flattened one level so RoMM doesn't read region folders as multi-part games.
set -uo pipefail
RSRC="seedbox:/home/hd34/btabaska/files"
ROMS=/volume1/games/romm/roms
EXTRAS=/volume1/games/romm-extras
RC="/usr/local/bin/rclone --config /root/.config/rclone/rclone.conf --transfers 12 --checkers 16 --stats 0"
LOG_TS() { printf '%s %s\n' "$(date '+%F %T')" "$*"; }
FAILS=0
run() { local lbl="$1"; shift; LOG_TS "-> $lbl"; "$@" || { LOG_TS "!! FAILED: $lbl (rc=$?)"; FAILS=$((FAILS+1)); }; }

mkdir -p "$EXTRAS/nes" "$EXTRAS/snes"

# --- small sets first (early RoMM wins) ---
run "gb: GAMEBOY COMPLETE"          $RC copy "$RSRC/GAMEBOY COMPLETE (U) [!] ROMSET" "$ROMS/gb"
run "gba: Nintendo Gameboy Advance" $RC copy "$RSRC/manual/Nintendo Gameboy Advance" "$ROMS/gba"

# nes: flatten the region dirs of the Sorted set
NES_SORTED="$RSRC/manual/Nintendo NES Complete ROMSET incl MiNI HackTool/NES Complete ROMSET incl MiNI HackTool/NES Roms Sorted"
while read -r d; do
  [ -n "$d" ] && run "nes: $d" $RC copy "$NES_SORTED/$d" "$ROMS/nes"
done < <($RC lsd "$NES_SORTED" 2>/dev/null | awk '{ $1=$2=$3=$4=""; sub(/^ +/,""); print }')
run "nes-extras: MINI HACK" $RC copy "$RSRC/manual/Nintendo NES Complete ROMSET incl MiNI HackTool/NES Complete ROMSET incl MiNI HackTool/NES MINI HACK" "$EXTRAS/nes/NES MINI HACK"

run "n64: extracted z64 set"       $RC copy "$RSRC/.rom-extract/n64/N64 Roms" "$ROMS/n64"
run "snes: extracted romset"       $RC copy "$RSRC/.rom-extract/snes/SNES Complete Romset" "$ROMS/snes"
run "snes-extras: box art"         $RC copy "$RSRC/manual/Super Nintendo (SNES) HyperSpin Set (ROMs + Covers + XML)/SNES Box Art" "$EXTRAS/snes/SNES Box Art"
run "snes-extras: hyperspin xml"   $RC copyto "$RSRC/manual/Super Nintendo (SNES) HyperSpin Set (ROMs + Covers + XML)/Super Nintendo Entertainment System.xml" "$EXTRAS/snes/Super Nintendo Entertainment System.xml"

# --- big sets ---
run "ngc: Gamecube Games"          $RC copy "$RSRC/manual/Nintendo Gamecube ISO Library + Emulators/Games" "$ROMS/ngc"
run "wiiu: Wii U Collection Redump" $RC copy "$RSRC/manual/Wii U Collection Redump" "$ROMS/wiiu"
for i in 1 2 3 4 5; do
  run "wii: Wii-Pack $i of 5"      $RC copy "$RSRC/manual/Wii-Pack $i of 5" "$ROMS/wii"
done

LOG_TS "normalizing ownership to 1026:100"
chown -R 1026:100 "$ROMS/gb" "$ROMS/gba" "$ROMS/nes" "$ROMS/n64" "$ROMS/snes" "$ROMS/ngc" "$ROMS/wiiu" "$ROMS/wii" "$EXTRAS"

LOG_TS "=== summary ==="
for p in gb gba nes n64 snes ngc wiiu wii; do
  LOG_TS "$p: $(find "$ROMS/$p" -type f | wc -l) files, $(du -sh "$ROMS/$p" 2>/dev/null | cut -f1)"
done
LOG_TS "failures: $FAILS"
[ "$FAILS" -eq 0 ] && echo DONE-OK > /volume1/games/.rom-import/STATUS || echo DONE-WITH-FAILURES > /volume1/games/.rom-import/STATUS
