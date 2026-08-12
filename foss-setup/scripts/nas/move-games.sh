#!/bin/bash
# move-games.sh — RELOCATE the complete game payloads from the seedbox into the
# NAS RomM library (2026-08-11). Uses `rclone move`: each file is verified on
# the NAS before it is deleted from the seedbox.
#
# 2026-08-11 22:00 REWRITE (operator correction): the PS3 torrent is 4.6T
# TOTAL but was only partially downloaded — 617G real data on seedbox disk.
# Sparse-block census (allocated >= size == complete, any hole = broken
# archive): 39/575 remaining archives complete (359 GiB); 536 were sparse
# hulls. The PS3 leg moves ONLY the complete archives, via --files-from
# ps3-complete.list. 2026-08-11 22:20 (operator decision): the hulls are NOT
# wanted — all 536 deleted from the seedbox, and the 10 broken first-run
# archives (all zero-holed on deep scan) deleted from the NAS quarantine.
# Only the 39 listed games survive; the other 546 would need a fresh
# re-download of the torrent if ever wanted.
# The NDS set censused fully complete (6573/6573 files) — moves whole.
# After both moves, a zero-run scan re-verifies every landed ps3 archive
# (any all-zero 1MiB chunk = a missed hole) and STATUS carries the count.
set -uo pipefail
RSRC="seedbox:/home/hd34/btabaska/files"
ROMS=/volume1/games/romm/roms
LOG=/volume1/games/.rom-import/move-games.log
STATUS=/volume1/games/.rom-import/STATUS-move
RC="/usr/local/bin/rclone --config /root/.config/rclone/rclone.conf --transfers 4 --checkers 8 --stats 5m --stats-one-line -v"
LOG_TS(){ printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }
echo "RUNNING $(date '+%F %T')" > "$STATUS"
LOG_TS "=== move-games start ==="

LOG_TS "-> ps3: complete archives only (39 files, 359G; see ps3-complete.list)"
$RC move "$RSRC/Sony PlayStation 3 (USA)" "$ROMS/ps3" --files-from /volume1/games/.rom-import/ps3-complete.list >>"$LOG" 2>&1
LOG_TS "ps3 rc=$?"

LOG_TS "-> nds: Nintendo_DS_Complete_Romset  (351G, 6573 roms, censused complete)"
$RC move "$RSRC/Nintendo_DS_Complete_Romset" "$ROMS/nds" --delete-empty-src-dirs >>"$LOG" 2>&1
LOG_TS "nds rc=$?"

LOG_TS "-> verify: ps3 zero-run scan (holes logged to $LOG)"
PS3HOLES=$(python3 - 2>>"$LOG" <<'PYEOF'
import glob, sys
Z = bytes(1024*1024)
n = 0
for path in sorted(glob.glob("/volume1/games/romm/roms/ps3/*.7z")):
    off = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(1024*1024)
            if not b:
                break
            if b == Z[:len(b)]:
                print("HOLE@%d %s" % (off, path), file=sys.stderr)
                n += 1
                break
            off += len(b)
print(n)
PYEOF
)
LOG_TS "ps3 zero-scan holes: ${PS3HOLES:-scan-failed}"

LOG_TS "normalizing ownership to 1026:100"
chown -R 1026:100 "$ROMS/ps3" "$ROMS/nds" 2>>"$LOG"
LOG_TS "summary: ps3=$(du -sh "$ROMS/ps3" 2>/dev/null|cut -f1) nds=$(du -sh "$ROMS/nds" 2>/dev/null|cut -f1)"
if [ "${PS3HOLES:-x}" = "0" ]; then echo "DONE $(date '+%F %T')" > "$STATUS"; else echo "DONE-PS3-HOLES=${PS3HOLES:-scan-failed} $(date '+%F %T')" > "$STATUS"; fi
LOG_TS "=== move-games end ==="
