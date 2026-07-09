#!/usr/bin/env bash
# net-selfheal — recover mini's primary NIC when its DHCP lease/route is lost.
#
# Root cause (2026-07-09): enp3s0f0 uses a pure-DHCP netplan config with a 24h
# lease. Lease renewal (T1 12h / T2 21h) silently fails, so at the 24h hard
# expiry systemd-networkd WITHDRAWS the address and flushes every route
# (RTM_DELROUTE). The box stays powered and the OS keeps running, but it is
# completely off the network (no ARP/ping/SSH/DNS) until a manual power-cycle.
# It looks "frozen" from outside but is not — it is networkless.
#
# This watchdog runs every minute (net-selfheal.timer). If the LAN gateway is
# unreachable it escalates renew -> link bounce -> networkd restart, logging
# every step to the journal (tag: net-selfheal) so the next incident is fully
# captured. When healthy it is a no-op.
set -uo pipefail
IF=enp3s0f0
GW=192.168.10.1
log(){ logger -t net-selfheal -- "$*"; }
pingok(){ ping -c1 -W2 "$GW" >/dev/null 2>&1; }
healthy(){
  ip -4 route show default 2>/dev/null | grep -q "via ${GW} dev ${IF}" || return 1
  pingok || pingok || pingok
}

healthy && exit 0

log "UNHEALTHY route=[$(ip -4 route show default | tr '\n' ' ')] addr=[$(ip -4 -o addr show "$IF" 2>/dev/null | awk '{print $4}' | tr '\n' ' ')]"

log "step1: networkctl renew ${IF}"
networkctl renew "$IF" 2>&1 | logger -t net-selfheal
sleep 5
healthy && { log "RECOVERED after renew"; exit 0; }

log "step2: link down/up ${IF}"
ip link set "$IF" down; sleep 2; ip link set "$IF" up; sleep 2
networkctl renew "$IF" 2>&1 | logger -t net-selfheal
sleep 8
healthy && { log "RECOVERED after link bounce"; exit 0; }

log "step3: systemctl restart systemd-networkd"
systemctl restart systemd-networkd 2>&1 | logger -t net-selfheal
sleep 8
healthy && { log "RECOVERED after networkd restart"; exit 0; }

log "STILL DOWN after all steps diag=[$(networkctl status "$IF" --no-pager 2>&1 | tr '\n' '|')]"
exit 1
