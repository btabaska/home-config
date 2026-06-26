#!/usr/bin/env bash
# tailscale-connectivity-test.sh
#
# Quick end-to-end reachability test across the tailnet. For each online peer it:
#   1) runs a Tailscale-layer ping (works even when ICMP is firewalled), and
#   2) optionally TCP-probes a service port (e.g. NAS 5001, SSH 22).
# Idempotent and read-only -- safe to run any time as a health check.
#
# Refs:
#   - tailscale ping / status:  https://tailscale.com/docs/reference/connection-types
#
# Usage:
#   ./tailscale-connectivity-test.sh
#   PORTS="22 5001 8123" ./tailscale-connectivity-test.sh    # also TCP-probe these ports
set -euo pipefail

PORTS="${PORTS:-}"
log()  { printf '\033[1;34m[conn]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  OK \033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m FAIL\033[0m %s\n' "$*"; }

command -v tailscale >/dev/null 2>&1 || { echo "tailscale not installed"; exit 1; }
tailscale status >/dev/null 2>&1 || { echo "tailscale is down -- run tailscale up first"; exit 1; }

# Collect peer DNSName + IP from the JSON status (jq if available, else fallback).
log "Discovering online peers..."
if command -v jq >/dev/null 2>&1; then
  mapfile -t PEERS < <(tailscale status --json \
    | jq -r '.Peer[] | select(.Online==true) | "\(.TailscaleIPs[0]) \(.HostName)"')
else
  # Fallback: parse the human-readable table (col1=IP, col2=host). Skips self/offline.
  mapfile -t PEERS < <(tailscale status | awk 'NF>=2 && $1 ~ /^100\./ {print $1" "$2}')
fi

[ "${#PEERS[@]}" -gt 0 ] || { log "No peers found."; exit 0; }

RC=0
for entry in "${PEERS[@]}"; do
  ip="${entry%% *}"; host="${entry##* }"
  log "Peer: ${host} (${ip})"

  if tailscale ping --c=1 --timeout=5s "$ip" >/dev/null 2>&1; then
    ok "  tailscale ping reachable"
  else
    fail "  tailscale ping FAILED"
    RC=1
  fi

  for port in $PORTS; do
    # /dev/tcp is a bash builtin; no nc dependency required.
    if timeout 3 bash -c ">/dev/tcp/${ip}/${port}" 2>/dev/null; then
      ok "  tcp/${port} open"
    else
      fail "  tcp/${port} closed/filtered"
      RC=1
    fi
  done
done

[ "$RC" -eq 0 ] && ok "All peers reachable." || fail "One or more checks failed."
exit "$RC"
