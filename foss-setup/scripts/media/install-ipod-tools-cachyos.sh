#!/usr/bin/env bash
# install-ipod-tools-cachyos.sh
#
# Idempotent install of the iPod Classic sync toolchain on CachyOS (Arch-based):
#   - rhythmbox  : simplest iPod sync (built-in libgpod-backed iPod support)
#   - libgpod    : the library that reads/writes Apple's iTunesDB (+ ipod tools)
#   - gtkpod     : power-user GUI (aging but handy for DB surgery)   [optional]
#   - hfsprogs   : fsck/mkfs for HFS+ iPods formatted on a Mac (AUR)  [optional]
#
# DECISION (see foss-setup-plan-2 §2 "iPod Classic"): keep Apple firmware +
# libgpod tooling so car/USB-controller integration stays intact. Music master
# stays on the NAS (Navidrome's library); the iPod is a reproducible copy.
#
# Safe to re-run: uses `pacman -S --needed`; AUR steps are skipped if the helper
# or package is already present.
#
# Refs:
#   - ArchWiki iPod:        https://wiki.archlinux.org/title/IPod
#   - libgpod project:      https://github.com/gtkpod/libgpod
#   - Rhythmbox:            https://wiki.gnome.org/Apps/Rhythmbox
#
# Usage:
#   ./install-ipod-tools-cachyos.sh                 # repo tools only
#   WITH_GTKPOD=1 ./install-ipod-tools-cachyos.sh    # also install gtkpod
#   WITH_HFSPROGS=1 ./install-ipod-tools-cachyos.sh  # also build hfsprogs (AUR)
set -euo pipefail

WITH_GTKPOD="${WITH_GTKPOD:-0}"
WITH_HFSPROGS="${WITH_HFSPROGS:-0}"

log()  { printf '\033[1;34m[ipod]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[ipod]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[ipod]\033[0m %s\n' "$*" >&2; exit 1; }

if [ "$(id -u)" -eq 0 ]; then
  die "Run as your normal user (the script calls sudo where needed)."
fi
command -v pacman >/dev/null 2>&1 || die "pacman not found — this script is for Arch/CachyOS."

# 1. Core repo packages (extra/community). libgpod ships the `ipod-*` CLI tools
#    (ipod-read-sysinfo-extended, etc.) that Rhythmbox/gtkpod rely on.
log "Installing core tools (rhythmbox, libgpod) via pacman"
sudo pacman -S --needed --noconfirm rhythmbox libgpod

# 2. Optional gtkpod GUI (power-user library editing / DB repair).
if [ "$WITH_GTKPOD" = "1" ]; then
  log "Installing gtkpod via pacman"
  sudo pacman -S --needed --noconfirm gtkpod
else
  log "Skipping gtkpod (set WITH_GTKPOD=1 to include it)"
fi

# 3. Optional hfsprogs (AUR) — only needed if your iPod is HFS+ formatted
#    (i.e. it was last initialized on a Mac). FAT32-formatted iPods don't need
#    this. AUR builds need an AUR helper (paru/yay) or a manual makepkg.
if [ "$WITH_HFSPROGS" = "1" ]; then
  if pacman -Qi hfsprogs >/dev/null 2>&1; then
    log "hfsprogs already installed"
  elif command -v paru >/dev/null 2>&1; then
    log "Building hfsprogs from AUR via paru"
    paru -S --needed --noconfirm hfsprogs
  elif command -v yay >/dev/null 2>&1; then
    log "Building hfsprogs from AUR via yay"
    yay -S --needed --noconfirm hfsprogs
  else
    warn "No AUR helper (paru/yay) found. Build manually:"
    warn "  git clone https://aur.archlinux.org/hfsprogs.git && cd hfsprogs && makepkg -si"
    warn "Or just re-format the iPod as FAT32 (see the runbook) to avoid HFS+ entirely."
  fi
else
  log "Skipping hfsprogs (set WITH_HFSPROGS=1 if your iPod is HFS+ formatted)"
fi

# 4. Report versions.
log "Installed versions:"
command -v rhythmbox >/dev/null 2>&1 && rhythmbox --version 2>/dev/null | head -1 || true
if command -v pkg-config >/dev/null 2>&1; then
  log "libgpod: $(pkg-config --modversion libgpod-1.0 2>/dev/null || echo 'n/a')"
fi
command -v gtkpod >/dev/null 2>&1 && log "gtkpod present" || true

cat <<'EOF'

[ipod] Next: plug in the iPod and follow ipod-sync-cachyos.md.
  - First sync of an iPod that has *never* touched iTunes may need a one-time
    DB initialization (and a FirewireGuid in SysInfo). The runbook covers it.
  - Keep the music master on the NAS (Navidrome library); the iPod is a copy.
EOF

log "Done."
