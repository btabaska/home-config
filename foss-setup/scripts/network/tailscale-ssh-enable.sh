#!/usr/bin/env bash
# tailscale-ssh-enable.sh
#
# Turn on Tailscale SSH on this node so it accepts SSH over the tailnet —
# key-less, ACL-gated, with nothing exposed to the public internet. Run it on
# every host you want to administer (Mac mini, NAS-where-supported, rig, seedbox).
# Idempotent: safe to re-run.
#
# The ACTUAL access policy (who may SSH which host as which user) lives in your
# tailnet ACLs, NOT here — apply configs/network/tailscale-acl-ssh.hujson in the
# Tailscale admin console (Access Controls). This script only flips the per-node
# "accept SSH" switch.
#
# Refs:
#   - Tailscale SSH:        https://tailscale.com/kb/1193/tailscale-ssh
#   - ACL syntax (ssh):     https://tailscale.com/kb/1337/acl-syntax
#
# Usage:
#   ./tailscale-ssh-enable.sh
set -euo pipefail

log() { printf '\033[1;34m[ts-ssh]\033[0m %s\n' "$*"; }

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale not installed — run tailscale-install-up.sh first." >&2
  exit 1
fi

# Make sure the node is actually up before toggling SSH.
if ! tailscale status >/dev/null 2>&1; then
  echo "This node is not logged in to a tailnet — run 'sudo tailscale up' first." >&2
  exit 1
fi

# `tailscale set --ssh` enables the SSH server without re-running the full `up`
# flow (no re-auth, no flag clobbering). Equivalent to adding --ssh to `up`.
log "Enabling Tailscale SSH on $(hostname -s)"
sudo tailscale set --ssh

log "Done. Node will accept SSH from peers permitted by your tailnet ACLs."
log "Next: apply configs/network/tailscale-acl-ssh.hujson in the admin console,"
log "then from a tag:admin device run:  ssh <user>@$(hostname -s)"
