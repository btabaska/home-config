#!/usr/bin/env bash
# Guarded static-IP apply for the mini (M2 — permanent fix for the recurring 24h
# DHCP-lease-expiry off-network outage). ONE-SHOT, self-testing, AUTO-REVERTING.
#
# Scheduled by apply-static-ip.timer to fire once in the 4-7AM ET maintenance
# window. Applies the static netplan, then runs a connectivity self-test; if any
# check fails it restores the DHCP config (the current known-good state) and pings
# ntfy. Worst case is therefore a safe no-op back to DHCP. net-selfheal.timer +
# KeepConfiguration remain as additional backstops.
#
# Deployed 2026-07-09 by the full audit remediation. Repo mirror lives beside the
# staged netplan in configs/host/mini/static-ip/.
set -uo pipefail

NP=/etc/netplan/00-installer-config.yaml
BAK="/etc/netplan/00-installer-config.yaml.pre-static-$(date -u +%Y%m%d%H%M%S)"
LOG=/var/log/apply-static-ip.log
IFACE=enp3s0f0
exec >>"$LOG" 2>&1
echo "=== $(date -u) apply-static-ip START ==="

# shellcheck disable=SC1091
source /etc/verification/env 2>/dev/null || true
notify() {
  curl -fsS -m 10 \
    -H "Authorization: Bearer ${NTFY_TOKEN:-}" \
    -H "Title: mini static-IP apply" \
    -d "$1" "${NTFY_URL:-http://127.0.0.1:8080}/verification" >/dev/null 2>&1 || true
}

finish() { systemctl disable apply-static-ip.timer >/dev/null 2>&1 || true; echo "=== $(date -u) apply-static-ip END ==="; }
trap finish EXIT

notify "starting guarded static-IP apply on mini (auto-reverts to DHCP if the self-test fails)"

cp -a "$NP" "$BAK"
echo "backed up $NP -> $BAK"

cat > "$NP" <<'YAML'
network:
  version: 2
  renderer: networkd
  ethernets:
    enp3s0f0:
      dhcp4: false
      dhcp6: false
      addresses: [192.168.10.2/24]
      routes:
        - to: default
          via: 192.168.10.1
          metric: 100
      nameservers:
        addresses: [192.168.10.2, 192.168.10.4, 192.168.10.1]
      link-local: [ipv6]
YAML
chmod 600 "$NP"

if ! netplan generate; then
  echo "netplan generate FAILED — reverting"
  cp -a "$BAK" "$NP"; netplan apply
  notify "FAILED at 'netplan generate'; reverted to DHCP. See $LOG"
  exit 1
fi

netplan apply
sleep 10

ok=1
ip -4 addr show "$IFACE" | grep -q "192.168.10.2/24" || { echo "FAIL: IP is not 192.168.10.2/24"; ok=0; }
ping -c2 -W3 192.168.10.1 >/dev/null 2>&1            || { echo "FAIL: gateway 192.168.10.1 unreachable"; ok=0; }
ping -c2 -W3 1.1.1.1 >/dev/null 2>&1                 || { echo "FAIL: external 1.1.1.1 unreachable"; ok=0; }
getent hosts home.tabaska.us | grep -q 192.168.10.2  || { echo "FAIL: DNS home.tabaska.us did not resolve to .2"; ok=0; }

if [ "$ok" -eq 1 ]; then
  echo "self-test PASS — keeping static 192.168.10.2"
  notify "OK: mini is now static 192.168.10.2. ACTION: add the UniFi Fixed-IP reservation for MAC 98:5a:eb:ca:b2:ef -> .2 to prevent a future lease conflict."
else
  echo "self-test FAILED — reverting to DHCP"
  cp -a "$BAK" "$NP"; netplan apply; sleep 8
  if ping -c2 -W3 192.168.10.1 >/dev/null 2>&1; then echo "revert OK (DHCP restored)"; else echo "WARN: still no gateway after revert — net-selfheal backstop should recover"; fi
  notify "static-IP self-test FAILED; reverted to DHCP (known-good). See $LOG"
fi
