#!/usr/bin/env bash
# syncthing-setup-cachyos.sh
#
# Idempotent install + enable of Syncthing as a systemd *user* service on
# CachyOS (Arch-based desktop). Use this to P2P-sync your Calibre/KOReader
# books + reading-progress files between the desktop, the NAS, and devices —
# no cloud involved.
#
# Safe to re-run: skips the pacman install if syncthing is already present and
# only enables the unit if it isn't already enabled.
#
# Why a *user* service (not syncthing@user.service):
#   - The user unit runs as you, with your $HOME and file ownership — exactly
#     what you want for syncing files in your home dir on a desktop.
#   - The system template unit (syncthing@.service) is meant for headless
#     servers. See the ArchWiki for the distinction.
#   - We enable `loginctl enable-linger` so Syncthing keeps running across
#     logout/reboot without an active graphical session.
#
# Refs:
#   - ArchWiki: https://wiki.archlinux.org/title/Syncthing
#   - Autostart: https://docs.syncthing.net/users/autostart.html
#   - First setup / GUI: https://docs.syncthing.net/intro/getting-started.html
#
# Usage:
#   ./syncthing-setup-cachyos.sh
#   The Web GUI then lives at http://127.0.0.1:8384 (add folders + remote
#   device IDs there). To reach the GUI from another LAN machine, see the note
#   printed at the end.
set -euo pipefail

log()  { printf '\033[1;34m[syncthing]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[syncthing]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[syncthing]\033[0m %s\n' "$*" >&2; exit 1; }

# 0. Sanity: this script targets a normal (non-root) desktop user, because the
#    systemd *user* instance and lingering are per-user.
if [ "$(id -u)" -eq 0 ]; then
  die "Run as your normal desktop user, not root (this sets up a --user service)."
fi
command -v pacman >/dev/null 2>&1 || die "pacman not found — this script is for Arch/CachyOS."

# 1. Install only if missing. Syncthing is in the Arch 'extra' repo and ships
#    the systemd unit files, so there is nothing to copy by hand.
if command -v syncthing >/dev/null 2>&1; then
  log "Already installed: $(syncthing --version 2>/dev/null | head -1)"
else
  log "Installing syncthing via pacman"
  sudo pacman -S --needed --noconfirm syncthing
fi

# 2. Reload user units so the freshly-installed /usr/lib/systemd/user/syncthing.service
#    is visible to the user manager.
systemctl --user daemon-reload || true

# 3. Enable lingering so the user service runs at boot without a login session.
#    Idempotent: enable-linger is a no-op if already enabled.
if loginctl show-user "$USER" --property=Linger 2>/dev/null | grep -q 'Linger=yes'; then
  log "Lingering already enabled for $USER"
else
  log "Enabling lingering for $USER (so Syncthing survives logout/reboot)"
  sudo loginctl enable-linger "$USER"
fi

# 4. Enable + start the user unit (idempotent — enabling an enabled unit is fine).
if systemctl --user is-enabled syncthing.service >/dev/null 2>&1; then
  log "syncthing.service already enabled"
else
  log "Enabling syncthing.service (user)"
  systemctl --user enable syncthing.service
fi
log "Starting/ensuring syncthing.service is running"
systemctl --user start syncthing.service

# 4.5 Open the firewall for Syncthing's sync ports (foss-03).
#     CachyOS ships ufw active by default. Without an inbound allow for 22000,
#     the always-on NAS hub cannot dial the rig directly, so the pair silently
#     falls back to a PUBLIC RELAY (cloud) — defeating the local-first goal.
#     Scope to the LAN; idempotent (ufw dedupes identical rules).
if command -v ufw >/dev/null 2>&1 && sudo ufw status 2>/dev/null | grep -q '^Status: active'; then
  log "Opening ufw for Syncthing (22000/tcp+udp, 21027/udp) from the LAN"
  sudo ufw allow from 192.168.10.0/24 to any port 22000 proto tcp comment 'syncthing sync (foss-03)'
  sudo ufw allow from 192.168.10.0/24 to any port 22000 proto udp comment 'syncthing quic (foss-03)'
  sudo ufw allow from 192.168.10.0/24 to any port 21027 proto udp comment 'syncthing discovery (foss-03)'
else
  warn "ufw not active — skipping firewall rules (ensure 22000/tcp+udp reachable on the LAN)."
fi

# 4.6 OPTIONAL: expose the Web GUI to the LAN so it can be reverse-proxied at
#     syncthing-rig.tabaska.us (mini Caddy) and surfaced on Homepage (foss-03).
#     GUARDED by SYNCTHING_GUI_PASSWORD so we NEVER expose an unauthenticated
#     admin panel: with no password set, the GUI stays localhost-only. The
#     password lives in the control-host vault (.handoff-secrets.yaml ->
#     syncthing.rig_gui_password); pass it in from there, e.g.:
#       SYNCTHING_GUI_PASSWORD=... SYNCTHING_GUI_USER=admin ./syncthing-setup-cachyos.sh
#     Applies live via the REST API (Syncthing v2 persists it to config.xml and
#     bcrypt-hashes the plaintext password on save).
if [ -n "${SYNCTHING_GUI_PASSWORD:-}" ]; then
  GUSER="${SYNCTHING_GUI_USER:-admin}"
  CFG="$HOME/.local/state/syncthing/config.xml"
  KEY=$(grep -oPm1 '(?<=<apikey>)[^<]+' "$CFG" 2>/dev/null || true)
  if [ -n "$KEY" ]; then
    log "Binding GUI to 0.0.0.0:8384 with admin auth (user '$GUSER') + opening ufw :8384 (LAN)"
    cur=$(curl -sf -H "X-API-Key: $KEY" http://127.0.0.1:8384/rest/config/gui 2>/dev/null || true)
    if [ -n "$cur" ]; then
      new=$(GUSER="$GUSER" GPW="$SYNCTHING_GUI_PASSWORD" python3 -c \
        'import sys,json,os; g=json.load(sys.stdin); g["address"]="0.0.0.0:8384"; g["user"]=os.environ["GUSER"]; g["password"]=os.environ["GPW"]; json.dump(g,sys.stdout)' <<<"$cur")
      if curl -sf -o /dev/null -X PUT -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
           -d "$new" http://127.0.0.1:8384/rest/config/gui; then
        log "GUI rebound to LAN with auth."
      else
        warn "GUI rebind PUT failed — check the REST API."
      fi
      if command -v ufw >/dev/null 2>&1 && sudo ufw status 2>/dev/null | grep -q '^Status: active'; then
        sudo ufw allow from 192.168.10.0/24 to any port 8384 proto tcp comment 'syncthing gui (foss-03)'
      fi
    else
      warn "Could not read current GUI config via REST — skipping LAN rebind."
    fi
  else
    warn "No API key found in $CFG — skipping LAN rebind."
  fi
else
  log "SYNCTHING_GUI_PASSWORD unset — leaving GUI on localhost (no LAN exposure)."
fi

# 5. Report status + where to go next.
sleep 1
if systemctl --user is-active syncthing.service >/dev/null 2>&1; then
  log "syncthing.service is active."
else
  warn "syncthing.service is not active yet — check: systemctl --user status syncthing.service"
fi

cat <<'EOF'

[syncthing] Next steps (do these in the Web GUI):
  1. Open http://127.0.0.1:8384 on this machine.
  2. Set a GUI username/password (Actions -> Settings -> GUI) before exposing
     anything; the default is unauthenticated on localhost only.
  3. Add the remote device IDs (NAS, Kobo's Syncthing/Möbius, phone). Each side
     shows its ID under Actions -> Show ID.
  4. Create a shared folder for your books (e.g. ~/Books or the Calibre library
     export) and/or the KOReader progress files, and share it to the NAS/device.

Reading-stack tips:
  - Books: sync a plain folder of EPUBs to the device; Calibre stays the master
    on the desktop and CWA auto-ingests on the NAS.
  - KOReader progress: KOReader stores per-book *.sdr/metadata.*.lua sidecars
    next to each book — sync the book folder and the sidecars travel with it.
    (For live cross-device progress, prefer CWA's built-in KOSync; Syncthing is
    the file-level belt-and-suspenders.)

Headless/remote GUI: this rig's GUI is reverse-proxied at
  https://syncthing-rig.tabaska.us (mini Caddy, LAN/Tailscale only) and its
  status shows on Homepage via the always-on NAS hub tile. To (re)apply the LAN
  bind + admin auth non-interactively, re-run this script with
  SYNCTHING_GUI_PASSWORD set (see section 4.6 / vault syncthing.rig_gui_password).
  Never bind 0.0.0.0 without a GUI password.
EOF

log "Done."
