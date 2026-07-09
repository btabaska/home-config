# Apply mini static IP (maintenance-window runbook)

Permanent fix for the recurring "mini frozen/off-network" outages — root cause was
24h DHCP lease expiry with failed in-lease renewal (RCA in
`docs/handoff-rollout-state.md`, 2026-07-09). This removes the lease dependency
entirely. Do this in the **4-7AM ET window**, ideally before a lease expiry.

Already-deployed safety nets remain in place and back this up:
`net-selfheal.timer` (recovers a dead link in ≤60s) and the `KeepConfiguration=dhcp`
drop-in (moot once static, remove in step 5).

## 0. Prerequisite (UniFi — user)
UniFi Network → Client Devices → **mini** (`98:5a:eb:ca:b2:ef`) → Settings →
**Fixed IP → 192.168.10.2**. This reserves .2 so DHCP never hands it to another
device. (Or exclude .2 from the DHCP pool.)

## 1-6. On mini (run with a TTY so `netplan try` can be confirmed)
```bash
# 2. back up current config
sudo cp /etc/netplan/00-installer-config.yaml /etc/netplan/00-installer-config.yaml.dhcp.bak

# 3. install the static config (from this repo dir)
sudo install -m 600 00-installer-config.static.yaml /etc/netplan/00-installer-config.yaml

# 4. validate + apply with auto-revert (must be an interactive TTY: ssh -t mini)
sudo netplan generate
sudo netplan try --timeout 120     # applies; press ENTER within 120s to KEEP, else auto-reverts

# 5. verify (in a SECOND terminal / fresh connection) BEFORE pressing Enter
ip -4 route show default                 # default via 192.168.10.1 dev enp3s0f0
ping -c2 192.168.10.1                     # gateway reachable
resolvectl query home.tabaska.us         # DNS still works
# from another host:  ssh mini 'echo ok'  &&  dig @192.168.10.2 +short home.tabaska.us
```
If all green, press **Enter** in the `netplan try` terminal to commit. If anything
is wrong, do nothing — it auto-reverts to DHCP in 120s.

## 5b. after static is confirmed committed
```bash
# KeepConfiguration drop-in is DHCP-only; harmless but tidy to remove:
sudo rm -f /etc/systemd/network/10-netplan-enp3s0f0.network.d/10-keepconfiguration.conf
sudo networkctl reload
```
Keep `net-selfheal.timer` — under static IP its `networkctl renew` step is a no-op,
but its link-bounce / networkd-restart escalation still recovers link faults.

## Rollback
```bash
sudo cp /etc/netplan/00-installer-config.yaml.dhcp.bak /etc/netplan/00-installer-config.yaml
sudo netplan apply
```

## Follow-up
Fold the static config + `net-selfheal` units into the ansible **mini** role so a
reprovision keeps them. Also worth: check the UniFi controller for why it wasn't
honoring in-lease RENEW/REBIND for this client (secondary; static makes it moot).
