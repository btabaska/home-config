#!/bin/bash
# move-games.sh — RELOCATE the two big already-on-disk game sets from the
# seedbox into the NAS RomM library (2026-08-11). Uses `rclone move`: each file
# is checksum-verified on the NAS before it is deleted from the seedbox, so
# seedbox space frees incrementally and nothing is lost. Their Deluge torrents
# were already removed (data kept) before this runs.
#
# 2026-08-11 21:45 (resume session): first run was SIGTERMed at 13:54:39
# (collateral of the seedbox rclone-mount remount cycle) after ~44G of ps3.
# Re-run is safe: already-moved files are gone from source, rclone continues
# with the rest. Size labels corrected — the PS3 set is 4.6T on seedbox disk
# (the original 625G figure was wrong), so this leg runs ~1.5-2 days. NOTE:
# the PS3 torrents were in Deluge Error state (incomplete) before removal —
# archive integrity is not guaranteed; a `7z t` sweep after the move is the
# way to find broken ones.
set -uo pipefail
RSRC="seedbox:/home/hd34/btabaska/files"
ROMS=/volume1/games/romm/roms
LOG=/volume1/games/.rom-import/move-games.log
STATUS=/volume1/games/.rom-import/STATUS-move
RC="/usr/local/bin/rclone --config /root/.config/rclone/rclone.conf --transfers 4 --checkers 8 --stats 5m --stats-one-line -v"
LOG_TS(){ printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }
echo "RUNNING $(date '+%F %T')" > "$STATUS"
LOG_TS "=== move-games start ==="

LOG_TS "-> ps3: Sony PlayStation 3 (USA)  (4.6T on disk, 585 archives)"
$RC move "$RSRC/Sony PlayStation 3 (USA)" "$ROMS/ps3" --delete-empty-src-dirs >>"$LOG" 2>&1
LOG_TS "ps3 rc=$?"

LOG_TS "-> nds: Nintendo_DS_Complete_Romset  (351G, 6573 roms)"
$RC move "$RSRC/Nintendo_DS_Complete_Romset" "$ROMS/nds" --delete-empty-src-dirs >>"$LOG" 2>&1
LOG_TS "nds rc=$?"

LOG_TS "normalizing ownership to 1026:100"
chown -R 1026:100 "$ROMS/ps3" "$ROMS/nds" 2>>"$LOG"
LOG_TS "summary: ps3=$(du -sh "$ROMS/ps3" 2>/dev/null|cut -f1) nds=$(du -sh "$ROMS/nds" 2>/dev/null|cut -f1)"
echo "DONE $(date '+%F %T')" > "$STATUS"
LOG_TS "=== move-games end ==="
