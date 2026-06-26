#!/usr/bin/env bash
# tailscale-verify-direct.sh
#
# Confirms peers are connected "direct" (peer-to-peer WireGuard) and NOT relayed
# through a DERP server. DERP works but is slower/higher-latency -- bad for
# game streaming, file sync, and backups. Also runs `netcheck` and flags the
# usual culprits (UDP blocked, symmetric NAT) and the UDP/41641 reminder.
#
# Refs:
#   - Connection types (direct vs DERP):  https://tailscale.com/docs/reference/connection-types
#   - netcheck fields / NAT traversal:    https://tailscale.com/kb/1082/firewall-ports/
#
# Usage:
#   ./tailscale-verify-direct.sh                 # check all peers
#   ./tailscale-verify-direct.sh nas cachyos     # also actively ping these peers until direct
set -euo pipefail

log()  { printf '\033[1;34m[verify]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  OK \033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m WARN\033[0m %s\n' "$*"; }

command -v tailscale >/dev/null 2>&1 || { echo "tailscale not installed"; exit 1; }

# --- 1. netcheck: is direct connectivity even possible from this host? ----------
log "Running 'tailscale netcheck' (NAT / UDP / DERP latency)..."
NETCHECK="$(tailscale netcheck 2>/dev/null || true)"
printf '%s\n' "$NETCHECK"

if printf '%s\n' "$NETCHECK" | grep -qiE 'UDP:\s*false'; then
  warn "UDP is BLOCKED outbound -> you will be stuck on DERP. Allow outbound UDP/41641 (+ UDP/3478 STUN)."
elif printf '%s\n' "$NETCHECK" | grep -qiE 'UDP:\s*true'; then
  ok "Outbound UDP works."
fi

if printf '%s\n' "$NETCHECK" | grep -qiE 'MappingVariesByDestIP:\s*true'; then
  warn "Symmetric NAT detected (MappingVariesByDestIP: true) -> direct may fail. Enable UPnP/PCP or port-forward UDP/41641."
fi

# --- 2. per-peer relay column from 'tailscale status' --------------------------
# A direct line looks like: "<ip> <peer> ... direct 1.2.3.4:41641"
# A relayed line looks like: "<ip> <peer> ... relay \"sfo\""
log "Per-peer connection paths ('direct' good, 'relay'/'derp' = relayed):"
RELAYED=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  case "$line" in
    *Health\ check*|*\#*) continue ;;
  esac
  if printf '%s' "$line" | grep -q 'direct'; then
    ok "$line"
  elif printf '%s' "$line" | grep -qiE 'relay|derp'; then
    warn "$line"
    RELAYED=$((RELAYED + 1))
  else
    printf '       %s\n' "$line"
  fi
done < <(tailscale status 2>/dev/null | tail -n +1)

# --- 3. optionally ping specific peers until a direct path is negotiated --------
# The first few pings often traverse DERP while NAT traversal finds a direct path.
for peer in "$@"; do
  log "Pinging '$peer' until direct (or timeout)..."
  if tailscale ping --until-direct --timeout=5s --c=10 "$peer"; then
    ok "$peer reachable directly."
  else
    warn "$peer did not establish a direct path (still on DERP). See UDP/41641 note below."
    RELAYED=$((RELAYED + 1))
  fi
done

echo
log "Reminder: a direct connection needs UDP port 41641 reachable on at least one side."
log "  - Enable UPnP/PCP on the Dream Wall, OR port-forward UDP/41641 to the relevant host."
log "  - On Ubuntu firewall (if enabled):  sudo ufw allow 41641/udp"

if [ "$RELAYED" -gt 0 ]; then
  warn "$RELAYED peer(s) relayed. Investigate before relying on this link for streaming/backups."
  exit 2
fi
ok "All checked peers are direct."
