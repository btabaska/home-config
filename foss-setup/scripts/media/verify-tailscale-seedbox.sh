#!/usr/bin/env bash
#
# verify-tailscale-seedbox.sh — confirm the off-site seedbox is on the tailnet and the home
#                               hosts can reach the *arr apps over it. Phase 2.
#
# Managed seedboxes are SHARED servers with NO root and NO TUN device, so you almost always run
# Tailscale in **userspace networking** mode from your home dir (static binaries + custom socket).
# This script auto-detects that socket and reports what's reachable. Run it ON THE SEEDBOX.
#
# Refs:
#   Userspace networking (no root/TUN): https://tailscale.com/kb/1112/userspace-networking/
#   Static binaries (download):         https://pkgs.tailscale.com/stable/#static
#   tailscale status / ping:            https://tailscale.com/kb/1080/cli/
#
# First-time install on a seedbox (userspace mode), for reference:
#   mkdir -p ~/tailscale && cd ~/tailscale
#   curl -fsSL "https://pkgs.tailscale.com/stable/tailscale_<VER>_amd64.tgz" -o ts.tgz
#   tar --strip-components=1 -xzf ts.tgz tailscale_<VER>_amd64/tailscale tailscale_<VER>_amd64/tailscaled
#   ./tailscaled --tun=userspace-networking \
#                --state=$HOME/tailscale/tailscaled.state \
#                --socket=$HOME/tailscale/tailscaled.sock --port=41641 &
#   ./tailscale --socket=$HOME/tailscale/tailscaled.sock up   # opens an auth URL
# (Wire that tailscaled command into a user systemd unit or the provider's "boot script" so it
#  survives reboots — see the userspace networking KB.)

set -euo pipefail

log()  { printf '\033[1;34m[ts-seedbox]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  OK \033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m WARN\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m FAIL\033[0m %s\n' "$*" >&2; exit 1; }

# --- Locate the tailscale CLI + the right socket (userspace mode uses a custom one) --------------
TS_BIN="${TS_BIN:-}"
if [[ -z "${TS_BIN}" ]]; then
  if command -v tailscale >/dev/null 2>&1; then TS_BIN="$(command -v tailscale)"
  elif [[ -x "$HOME/tailscale/tailscale" ]]; then TS_BIN="$HOME/tailscale/tailscale"
  elif [[ -x "$HOME/.local/bin/tailscale" ]]; then TS_BIN="$HOME/.local/bin/tailscale"
  else die "tailscale binary not found. Install static binaries: https://pkgs.tailscale.com/stable/#static"
  fi
fi

# Build a CLI invocation that uses the userspace socket if present.
TS_SOCKET="${TS_SOCKET:-}"
if [[ -z "${TS_SOCKET}" ]]; then
  for cand in "$HOME/tailscale/tailscaled.sock" "$HOME/.tmp/tailscale/tailscaled.sock" "/var/run/tailscale/tailscaled.sock"; do
    [[ -S "$cand" ]] && { TS_SOCKET="$cand"; break; }
  done
fi
TS=( "${TS_BIN}" )
[[ -n "${TS_SOCKET}" ]] && TS+=( --socket="${TS_SOCKET}" )
log "Using: ${TS[*]}"

# --- 1. Is this node up on the tailnet? ----------------------------------------------------------
if ! STATUS="$("${TS[@]}" status 2>&1)"; then
  warn "$STATUS"
  die "tailscaled not reachable. Start it (userspace mode) and run '${TS[*]} up'."
fi

if printf '%s' "$STATUS" | grep -qiE 'Logged out|NeedsLogin|Stopped'; then
  die "Seedbox is NOT logged in to the tailnet. Run: ${TS[*]} up"
fi
ok "Seedbox is up on the tailnet."

SELF_IP="$("${TS[@]}" ip -4 2>/dev/null | head -n1 || true)"
[[ -n "${SELF_IP}" ]] && ok "This node's Tailscale IP: ${SELF_IP}"
printf '%s\n' "$STATUS"

# --- 2. Reachability to the HOME peers that matter -----------------------------------------------
# Override with: PEERS="mac-mini nas" ./verify-tailscale-seedbox.sh
PEERS=( ${PEERS:-} )
if [[ ${#PEERS[@]} -eq 0 ]]; then
  warn "No PEERS given. Re-run e.g.: PEERS=\"mac-mini nas\" $0   (the home Seerr host + NAS)"
else
  for peer in "${PEERS[@]}"; do
    log "Pinging '${peer}' over Tailscale..."
    if "${TS[@]}" ping --c=4 --timeout=5s "${peer}" >/dev/null 2>&1; then
      ok "${peer} reachable."
    else
      warn "${peer} NOT reachable. Check it's online, shares the tailnet, and ACLs allow it."
    fi
  done
fi

# --- 3. Local *arr ports listening (so Seerr at home can reach them over the tailnet) ------------
# Userspace mode reaches local services fine; this just confirms the apps are actually up.
log "Checking *arr web ports are listening locally:"
declare -A PORTS=( [Sonarr]=8989 [Radarr]=7878 [Prowlarr]=9696 [qBittorrent]=8080 [Bazarr]=6767 )
checker=""
command -v ss >/dev/null 2>&1 && checker="ss" || { command -v netstat >/dev/null 2>&1 && checker="netstat"; }
for app in "${!PORTS[@]}"; do
  p="${PORTS[$app]}"
  listening=1
  if [[ "$checker" == "ss" ]]; then
    ss -tlnp 2>/dev/null | grep -q ":${p} " || listening=0
  elif [[ "$checker" == "netstat" ]]; then
    netstat -tln 2>/dev/null | grep -q ":${p} " || listening=0
  else
    # Fallback: probe with curl.
    curl -s -o /dev/null --max-time 2 "http://localhost:${p}" && listening=1 || listening=0
  fi
  if [[ "$listening" == "1" ]]; then ok "${app} listening on :${p}"; else warn "${app} not detected on :${p} (install/start it, or adjust the port)"; fi
done

echo
log "Reminder: in Seerr (home) add Sonarr/Radarr using this node's Tailscale name/IP (${SELF_IP:-100.x.y.z}),"
log "and point rclone.conf 'host' at the same name so seedbox-sync.sh rides the tailnet."
ok "Verification complete."
