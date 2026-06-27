#!/usr/bin/env bash
# zbf-isolation-verify.sh
#
# Verify UniFi ZBF isolation policies (net-05 "Done when" criteria) from a client on
# any VLAN. Auto-detects zone from the local IP when using the 192.168.{vlan}.0/24 scheme
# from vlan-zone-firewall-plan.md, or set ZONE= explicitly.
#
# Usage:
#   ./zbf-isolation-verify.sh                          # auto-detect zone
#   ZONE=iot TRUSTED_IP=192.168.10.50 ./zbf-isolation-verify.sh
#   ZONE=work TRUSTED_IP=192.168.10.1 ./zbf-isolation-verify.sh
#   ZONE=trusted IOT_IP=192.168.20.10 ./zbf-isolation-verify.sh
#
# Refs:
#   - configs/network/firewall-policy-walkthrough.md
#   - configs/network/firewall-policy-order.md
set -euo pipefail

INTERNET_IP="${INTERNET_IP:-8.8.8.8}"
TRUSTED_IP="${TRUSTED_IP:-192.168.10.1}"
IOT_IP="${IOT_IP:-192.168.20.1}"
PING_COUNT="${PING_COUNT:-2}"
PING_TIMEOUT="${PING_TIMEOUT:-3}"

log()  { printf '\033[1;34m[zbf]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  OK \033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m FAIL\033[0m %s\n' "$*"; }
skip() { printf '\033[1;33m SKIP\033[0m %s\n' "$*"; }

ping_ok() {
  local target="$1"
  ping -c "$PING_COUNT" -W "$PING_TIMEOUT" "$target" >/dev/null 2>&1
}

ping_fail() {
  local target="$1"
  ! ping -c "$PING_COUNT" -W "$PING_TIMEOUT" "$target" >/dev/null 2>&1
}

local_ip() {
  if command -v ip >/dev/null 2>&1; then
    ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}'
  elif command -v ipconfig >/dev/null 2>&1; then
    for iface in en0 en1; do
      ipconfig getifaddr "$iface" 2>/dev/null && return 0
    done
    return 1
  else
    hostname -I 2>/dev/null | awk '{print $1}'
  fi
}

detect_zone() {
  local ip="${1:-}"
  [[ -n "$ip" ]] || ip="$(local_ip || true)"
  [[ -n "$ip" ]] || { echo "Could not detect local IP; set ZONE= explicitly." >&2; exit 1; }

  case "$ip" in
    192.168.1.*|192.168.0.*) echo "internal" ;;
    192.168.10.*) echo "trusted" ;;
    192.168.20.*) echo "iot" ;;
    192.168.30.*) echo "cameras" ;;
    192.168.40.*) echo "work" ;;
    192.168.50.*) echo "guest" ;;
    *)
      echo "unknown" >&2
      echo "Local IP ${ip} does not match the 192.168.{vlan}.x scheme." >&2
      echo "Set ZONE=trusted|iot|cameras|work|guest|internal explicitly." >&2
      exit 1
      ;;
  esac
}

ZONE="${ZONE:-$(detect_zone)}"
LOCAL_IP="$(local_ip 2>/dev/null || true)"
log "Zone: ${ZONE} (local IP: ${LOCAL_IP:-unknown})"

RC=0
expect_ping_ok() {
  local label="$1" target="$2"
  if ping_ok "$target"; then ok "$label ($target reachable)"; else fail "$label ($target unreachable)"; RC=1; fi
}
expect_ping_fail() {
  local label="$1" target="$2"
  if ping_fail "$target"; then ok "$label ($target blocked as expected)"; else fail "$label ($target reachable — should be blocked)"; RC=1; fi
}

case "$ZONE" in
  trusted)
    log "Trusted: should reach IoT and internet; IoT isolation is tested from IoT VLAN."
    expect_ping_ok "Trusted → IoT (gateway)" "$IOT_IP"
    expect_ping_ok "Trusted → Internet" "$INTERNET_IP"
    skip "IoT→Trusted block — run this script from an IoT device to verify"
    skip "Cameras no internet — run from Cameras VLAN"
    skip "Work/Guest isolation — run from Work or Guest VLAN"
    ;;
  iot)
    log "IoT: should reach internet + gateway DNS path; must NOT reach Trusted."
    expect_ping_ok "IoT → Internet" "$INTERNET_IP"
    expect_ping_fail "IoT → Trusted (isolation)" "$TRUSTED_IP"
    ;;
  cameras)
    log "Cameras: should NOT reach internet or internal zones."
    expect_ping_fail "Cameras → Internet (blocked)" "$INTERNET_IP"
    expect_ping_fail "Cameras → Trusted (isolation)" "$TRUSTED_IP"
    ;;
  work|guest)
    zone_label="$(printf '%s' "$ZONE" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
    log "${zone_label}: internet only — should reach internet, NOT internal."
    expect_ping_ok "${zone_label} → Internet" "$INTERNET_IP"
    expect_ping_fail "${zone_label} → Trusted (isolation)" "$TRUSTED_IP"
    ;;
  internal)
    log "Internal (mgmt): full access expected — smoke test only."
    expect_ping_ok "Internal → Internet" "$INTERNET_IP"
    expect_ping_ok "Internal → Trusted" "$TRUSTED_IP"
    ;;
  *)
    echo "Unknown ZONE=${ZONE}. Use: trusted, iot, cameras, work, guest, internal." >&2
    exit 1
    ;;
esac

if [ "$RC" -eq 0 ]; then
  ok "All checks passed for zone=${ZONE}."
else
  fail "One or more checks failed for zone=${ZONE}."
fi
exit "$RC"
