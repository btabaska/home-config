#!/usr/bin/env bash
# tailscale-install-up.sh
#
# Idempotent install + bring-up of Tailscale on Ubuntu Server (Mac mini host).
# Safe to re-run: skips install if already present, skips `up` if already logged in.
#
# Refs:
#   - Install on Linux:        https://tailscale.com/docs/install/linux
#   - Connection types/ports:  https://tailscale.com/docs/reference/connection-types
#
# Usage:
#   ./tailscale-install-up.sh                 # interactive login (prints a URL to open)
#   TS_HOSTNAME=macmini ./tailscale-install-up.sh
#   TS_AUTHKEY=tskey-auth-xxxx ./tailscale-install-up.sh   # unattended/headless
set -euo pipefail

TS_HOSTNAME="${TS_HOSTNAME:-$(hostname -s)}"
TS_AUTHKEY="${TS_AUTHKEY:-}"

log() { printf '\033[1;34m[tailscale]\033[0m %s\n' "$*"; }

# 1. Install only if the binary is missing. The official script adds the upstream
#    apt repo, imports the signing key, installs the pkg, and enables tailscaled.
if command -v tailscale >/dev/null 2>&1; then
  log "Already installed: $(tailscale version | head -1)"
else
  log "Installing via official script (curl -fsSL https://tailscale.com/install.sh | sh)"
  curl -fsSL https://tailscale.com/install.sh | sh
fi

# 2. Make sure the daemon is enabled + running (the installer normally does this,
#    but we assert it so the script is safe on partially-configured hosts).
if command -v systemctl >/dev/null 2>&1; then
  log "Ensuring tailscaled is enabled and running"
  sudo systemctl enable --now tailscaled
fi

# 3. Bring the node up only if it is not already in a Running state.
#    `tailscale status` exits non-zero when logged out / stopped.
if tailscale status >/dev/null 2>&1; then
  log "Node is already up:"
  tailscale status || true
else
  log "Bringing node up as hostname=${TS_HOSTNAME}"
  if [ -n "${TS_AUTHKEY}" ]; then
    sudo tailscale up --hostname="${TS_HOSTNAME}" --auth-key="${TS_AUTHKEY}" --qr=false
  else
    log "Interactive login: open the URL below in a browser already signed in to your tailnet."
    sudo tailscale up --hostname="${TS_HOSTNAME}" --qr=false
  fi
fi

log "Tailscale IPv4: $(tailscale ip -4 2>/dev/null || echo 'n/a')"
log "Done. Verify peer paths with ./tailscale-verify-direct.sh"
