#!/usr/bin/env bash
#
# cachyos-desktop-baseline.sh
# Install the browser + office baseline on the CachyOS (Arch) rig.
#
# What it sets up:
#   * A browser (default: Firefox from the official repo). Optionally LibreWolf
#     (hardened) and/or Zen (Firefox-based, polished) from the AUR.
#   * LibreOffice (default: libreoffice-fresh, the 26.2 current branch) for
#     offline office work. Set LIBREOFFICE_PKG=libreoffice-still for the prior
#     (more conservative) maintenance branch, or =none to skip.
#
# Setting Kagi as the default search engine is a per-profile *browser* action and
# cannot be reliably scripted — it's documented at the end and printed on finish.
#
# Docs:
#   - LibreOffice on Arch:   https://wiki.archlinux.org/title/LibreOffice
#   - Firefox on Arch:       https://wiki.archlinux.org/title/Firefox
#   - LibreWolf:             https://librewolf.net/installation/arch/
#   - Zen browser (AUR):     https://aur.archlinux.org/packages/zen-browser-bin
#   - Kagi default search:   https://help.kagi.com/kagi/getting-started/setting-default.html
#
# Idempotent: pacman/AUR installs use --needed, so re-running is a no-op for
# already-installed packages. Do NOT run as root — AUR builds must run as a normal
# user; the script calls sudo only where needed.
#
# Usage:
#   ./cachyos-desktop-baseline.sh                       # Firefox + LibreOffice (default)
#   BROWSERS="firefox zen" ./cachyos-desktop-baseline.sh
#   BROWSERS="firefox librewolf zen" ./cachyos-desktop-baseline.sh
#   LIBREOFFICE_PKG=libreoffice-still ./cachyos-desktop-baseline.sh   # prior branch instead
#   LIBREOFFICE_PKG=none ./cachyos-desktop-baseline.sh                # skip office
set -euo pipefail

BROWSERS="${BROWSERS:-firefox}"               # space-separated: firefox librewolf zen
LIBREOFFICE_PKG="${LIBREOFFICE_PKG:-libreoffice-fresh}"  # 26.2 current branch (recommended); libreoffice-still=prior branch; 'none' to skip

log()  { printf '\033[1;32m[desktop]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[desktop][!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[desktop][x]\033[0m %s\n' "$*" >&2; exit 1; }

[[ "${EUID}" -ne 0 ]] || die "Do not run as root. Run as your normal user; sudo is invoked where needed."
command -v pacman >/dev/null 2>&1 || die "pacman not found — this script targets Arch/CachyOS."

# Detect an AUR helper for LibreWolf/Zen. CachyOS ships paru; yay is also common.
AUR_HELPER=""
detect_aur_helper() {
  if command -v paru >/dev/null 2>&1; then AUR_HELPER="paru"
  elif command -v yay >/dev/null 2>&1; then AUR_HELPER="yay"
  fi
}

pac_install() {
  # Install official-repo packages idempotently.
  log "pacman -S --needed $*"
  sudo pacman -S --needed --noconfirm "$@"
}

aur_install() {
  # Install AUR packages idempotently via the detected helper.
  [[ -n "${AUR_HELPER}" ]] || die "Need an AUR helper (paru/yay) for: $*. Install one, e.g. 'sudo pacman -S --needed paru'."
  log "${AUR_HELPER} -S --needed $*"
  "${AUR_HELPER}" -S --needed --noconfirm "$@"
}

install_browsers() {
  local b
  for b in ${BROWSERS}; do
    case "${b}" in
      firefox)
        # Official repo — the safe, low-maintenance default.
        pac_install firefox
        ;;
      librewolf)
        # Hardened Firefox fork. Not in Arch's official repos; use the -bin AUR
        # package (precompiled — building from source takes ages). Flatpak
        # (app: io.gitlab.librewolf-community) is the alternative.
        aur_install librewolf-bin
        ;;
      zen)
        # Firefox-based, polished. AUR precompiled binary (vetted, high-vote).
        aur_install zen-browser-bin
        ;;
      *)
        warn "Unknown browser '${b}' — skipping. Valid: firefox librewolf zen."
        ;;
    esac
  done
}

install_office() {
  if [[ "${LIBREOFFICE_PKG}" == "none" ]]; then
    log "Skipping LibreOffice (LIBREOFFICE_PKG=none)."
    return 0
  fi
  # libreoffice-fresh = 26.2 current branch (recommended; default here).
  # libreoffice-still = prior maintenance branch (more conservative). Both in 'extra'.
  # Language packs auto-detect locale; add e.g. libreoffice-still-<lang> if needed.
  log "Installing ${LIBREOFFICE_PKG} (LibreOffice desktop)."
  pac_install "${LIBREOFFICE_PKG}"
}

print_kagi_instructions() {
  cat <<'EOF'

==============================================================================
 MANUAL STEP — set Kagi as your default search engine (per browser profile)
==============================================================================
Easiest (Firefox / Zen / LibreWolf are all Firefox-based):
  1. Install the "Kagi Search" extension from addons.mozilla.org — it will offer
     to set Kagi as default; click Yes.

Manual (no extension):
  1. Open  about:preferences#search
  2. Under "Search Shortcuts" click "Add" and enter:
       Name:  Kagi
       URL:   https://kagi.com/search?q=%s
  3. (optional) Suggestions URL: https://kagi.com/api/autosuggest?q=%s
  4. Set the "Default Search Engine" dropdown to Kagi.

Docs: https://help.kagi.com/kagi/getting-started/setting-default.html

Hardening note: LibreWolf ships locked-down defaults (disables telemetry, clears
data on close by default). If you pick LibreWolf, review Settings so it doesn't
wipe your Kagi session/logins on exit (adjust "Delete cookies and site data on
close" exceptions for kagi.com and your self-hosted services).
==============================================================================
EOF
}

main() {
  detect_aur_helper
  # NOTE: deliberately NO bare `pacman -Sy` here. On a rolling release a lone
  # -Sy (refresh the sync db WITHOUT upgrading) creates a partial-upgrade hazard:
  # a subsequent install can pull a package built against newer libraries than the
  # ones currently installed, which can break the system. We install with --needed
  # against the CURRENT sync db instead, so the deps we pull match what's installed.
  # If a target package is missing or too old, run a FULL `sudo pacman -Syu` first
  # (in a maintenance window — it may bump the kernel/nvidia and want a reboot),
  # then re-run this script.
  # https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported
  install_browsers
  install_office
  log "Baseline installed. Browsers: ${BROWSERS}. Office: ${LIBREOFFICE_PKG}."
  print_kagi_instructions
}

main "$@"
