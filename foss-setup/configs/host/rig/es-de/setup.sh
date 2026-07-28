#!/usr/bin/env bash
# retro-05 — ES-DE (EmulationStation Desktop Edition) + RetroArch on the rig,
# pointed at the SAME NAS ROM library that RomM (mini /opt/stacks/romm) manages.
#
# Documentation-only / reproducible installer. NOT ansible-managed (the rig's
# site.yml converges only base/docker/tailscale/backup/state) — run by hand on
# the rig (CachyOS 192.168.10.12) as user `btabaska`. Land every change here AND
# on the live host (anti-drift).
#
# Design
# ------
# * ROM source of truth = the NAS `games` SMB share, already CIFS-mounted on the
#   rig at /mnt/share/Games (see configs/host/rig/nas-mounts/). RomM's library
#   root is /mnt/share/Games/romm/roms/<romm-slug>/. RomM (mini) and ES-DE (rig)
#   read the exact same on-disk files — no copy, no second sync.
# * ES-DE expects ROMs under a ROMDirectory (default ~/ROMs) laid out as
#   ~/ROMs/<es-de-system>/. We bridge ES-DE's system names to RomM's platform
#   slugs with a tree of per-system SYMLINKS into the NAS mount, so ES-DE browses
#   the live library read-only and never writes to the NAS share (its gamelists,
#   downloaded media and config stay local under ~/ES-DE/).
#   The only name that differs is GameCube: ES-DE `gc` -> RomM slug `ngc`.
# * Emulators: native RetroArch + libretro cores from the CachyOS repos. ES-DE's
#   bundled es_systems.xml already defaults each of these 7 systems to the core
#   we install (verified 2026-07-28), so no custom es_systems.xml is needed:
#       gb   -> gambatte      nes  -> mesen          n64  -> mupen64plus_next
#       gba  -> mgba          snes -> snes9x         gc   -> dolphin (libretro)
#                                                    wii  -> dolphin (libretro)
#   Wii U is intentionally NOT wired: ES-DE's `wiiu` system needs the Cemu
#   standalone (AUR) and .wua/.wux/.rpx ROMs; the 34 files currently in the RomM
#   `wiiu` slug are .zip and do not match, so ES-DE skips that system. Deferred.
set -euo pipefail

ROMBASE=/mnt/share/Games/romm/roms      # RomM library root on the NAS games share
ROMDIR="$HOME/ROMs"                     # ES-DE default ROMDirectory

# 1) Packages ---------------------------------------------------------------
# RetroArch + the six libretro cores that back our 7 systems + core-info DB.
sudo pacman -S --needed --noconfirm \
  retroarch libretro-core-info \
  libretro-gambatte libretro-mgba libretro-mesen \
  libretro-snes9x libretro-mupen64plus-next libretro-dolphin

# ES-DE itself is AUR (builds from source; pulls freeimage/pugixml).
paru -S --needed --noconfirm emulationstation-de

# 2) ROM symlink tree (ES-DE system name -> RomM platform slug) -------------
mkdir -p "$ROMDIR"
# associative map; only gc differs from the RomM slug (ngc)
declare -A MAP=( [gb]=gb [gba]=gba [n64]=n64 [nes]=nes [snes]=snes [gc]=ngc [wii]=wii [wiiu]=wiiu )
for sys in "${!MAP[@]}"; do
  ln -sfn "$ROMBASE/${MAP[$sys]}" "$ROMDIR/$sys"
done

echo "ES-DE ROM symlinks under $ROMDIR:"
ls -l "$ROMDIR"

# 3) First run generates ~/ES-DE/ (settings, gamelists, bundled themes). ES-DE
#    uses the default ROMDirectory (~/ROMs) — es_settings.xml ROMDirectory is
#    left empty, which means "default". Launch once from the Plasma session:
#      es-de
#    It parses the bundled es_systems.xml (195 systems), loads the 7 that have
#    ROMs and reports the total game count in ~/ES-DE/logs/es_log.txt.
echo "Done. Launch 'es-de' from the graphical session to browse + play."
