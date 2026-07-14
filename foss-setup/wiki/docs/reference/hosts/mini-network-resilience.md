# mini — network resilience (static IP + net-selfheal watchdog)

> How the recurring "frozen mini" off-network outages were root-caused (24h DHCP lease expiry) and permanently fixed: a static-IP conversion plus a `net-selfheal` per-minute watchdog and a `KeepConfiguration=dhcp` backstop.

_Source: `foss-setup/configs/host/mini/static-ip/README-apply.md`, `foss-setup/configs/host/mini/static-ip/apply-static-ip.service`, `foss-setup/configs/host/mini/static-ip/apply-static-ip.timer`, `foss-setup/configs/host/mini/net-selfheal/net-selfheal.service`, `foss-setup/configs/host/mini/net-selfheal/net-selfheal.timer` · migrated + validated 2026-07-14_

## Root cause (RCA 2026-07-09)

The recurring "mini frozen / off the network" incidents were **not** a lockup. `mini` (`192.168.10.2`, MAC `98:5a:eb:ca:b2:ef`, NIC `enp3s0f0`) ran a bare `dhcp4: true` netplan config with a **24h DHCP lease**. In-lease renewal (T1 at 12h, T2 at 21h) silently failed, so at the **24h hard expiry** `systemd-networkd` **withdrew the address and flushed every route** (`RTM_DELROUTE`). The box stayed powered and the OS kept running, but it was completely off the network — no ARP / ping / SSH / DNS — until a manual power-cycle. It **looked** frozen from outside but was only networkless.

Full RCA lives in `foss-setup/docs/handoff-rollout-state.md` (2026-07-09 entry).

Three fixes were layered, in escalating permanence:

| Layer | What it does | Status |
| --- | --- | --- |
| `KeepConfiguration=dhcp` drop-in | Keeps the DHCP address + routes if the lease can't be renewed | Deployed 2026-07-09; now moot but still present |
| `net-selfheal.timer` | Per-minute watchdog: recovers a dead link in ≤60s via renew → link-bounce → networkd-restart escalation | Deployed 2026-07-09, enabled, active |
| Static IP (netplan `dhcp4: false`) | Removes the lease dependency entirely — the permanent fix | Applied + committed 2026-07-10 |

!!! note "Validated against live mini (2026-07-14)"
    The static-IP conversion is **DONE**, not open. Live `/etc/netplan/00-installer-config.yaml` has `dhcp4: false` with `addresses: [192.168.10.2/24]`; `ip -4 addr show enp3s0f0` reports `192.168.10.2/24`; `ip -4 route show default` is `default via 192.168.10.1 dev enp3s0f0 proto static metric 100`. A pre-static backup `00-installer-config.yaml.pre-static-20260710083500` exists. `apply-static-ip.service` ran `status=0/SUCCESS` at 2026-07-10 08:35:15 UTC and its one-shot timer disabled itself (`apply-static-ip.timer` is now `disabled` — expected). `net-selfheal.timer` is `enabled` + `active (waiting)`, firing every 60s; `journalctl -t net-selfheal` shows **No entries** (healthy no-op since deploy → the fix is holding).

## The static-IP config

Live `/etc/netplan/00-installer-config.yaml` (mode `600`, root:root), identical to the staged `00-installer-config.static.yaml` in the repo dir and the heredoc written by `apply-static-ip.sh`:

```yaml
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
        # parity with the DHCP-provided link DNS (AdGuard on mini, then nas, then gw)
        addresses: [192.168.10.2, 192.168.10.4, 192.168.10.1]
      link-local: [ipv6]
```

Nameserver order: `192.168.10.2` (AdGuard on mini itself) → `192.168.10.4` (nas) → `192.168.10.1` (gateway).

### UniFi prerequisite (done)

UniFi already has a **Fixed-IP reservation for `98:5a:eb:ca:b2:ef` → 192.168.10.2** (confirmed 2026-07-09), so `.2` can be hard-coded static with no conflict risk. The reservation being present is also a clue: DHCP *should* answer renewals with `.2` — that it didn't points to a UniFi RENEW/REBIND-handling quirk or a networkd DHCP-client issue. Going static sidesteps both.

## Guarded apply mechanism (how it was rolled out safely)

Rather than risk locking the operator out during the change, the apply was automated as a **one-shot, self-testing, auto-reverting** unit fired inside the 4-7AM ET maintenance window.

### `apply-static-ip.service`

```ini
[Unit]
Description=Guarded one-shot static-IP apply for mini (M2, auto-reverts to DHCP on failure)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/apply-static-ip.sh
```

### `apply-static-ip.timer`

```ini
[Unit]
Description=Fire the guarded static-IP apply once in tonight's 4-7AM ET window
# NOTE: mini runs UTC + systemd 249 (no TZ suffix in OnCalendar); 08:35 UTC = 04:35 EDT.
# One-shot: the apply script disables this timer on completion. Re-arm by editing
# OnCalendar to a future window date and `systemctl enable --now apply-static-ip.timer`.

[Timer]
OnCalendar=2026-07-10 08:35:00 UTC
Persistent=false
AccuracySec=1min

[Install]
WantedBy=timers.target
```

`08:35 UTC = 04:35 EDT`. Because mini runs systemd 249 which doesn't take a TZ suffix in `OnCalendar`, the window is expressed in UTC. `Persistent=false` — if the box is off at fire time it does **not** catch up.

### `/usr/local/sbin/apply-static-ip.sh` (behavior)

The script (`set -uo pipefail`, logs to `/var/log/apply-static-ip.log`, sources `/etc/verification/env` for ntfy creds):

1. `notify` via ntfy that a guarded apply is starting (`Authorization: Bearer $NTFY_TOKEN`, `Title: mini static-IP apply`, POST to `${NTFY_URL:-http://127.0.0.1:8080}/verification`).
2. Back up the current netplan to `/etc/netplan/00-installer-config.yaml.pre-static-$(date -u +%Y%m%d%H%M%S)`.
3. Write the static YAML heredoc to `/etc/netplan/00-installer-config.yaml`, `chmod 600`.
4. `netplan generate` — on failure, restore backup, `netplan apply`, notify, exit 1.
5. `netplan apply`, `sleep 10`, then a 4-check self-test (`ok=1` unless any fails):
   - `ip -4 addr show enp3s0f0` contains `192.168.10.2/24`
   - `ping -c2 -W3 192.168.10.1` (gateway) succeeds
   - `ping -c2 -W3 1.1.1.1` (external) succeeds
   - `getent hosts home.tabaska.us` resolves to `192.168.10.2`
6. **PASS** → keep static, notify OK (with the reminder to add the UniFi fixed-IP reservation). **FAIL** → restore the DHCP backup, `netplan apply`, sleep 8, re-check gateway, notify failure. Worst case is a safe no-op back to DHCP.
7. `trap finish EXIT` always runs `systemctl disable apply-static-ip.timer` (makes it truly one-shot) and prints an END marker.

### Manual interactive alternative (runbook, if re-doing by hand)

Run with a TTY so `netplan try` can be confirmed (`ssh -t mini`):

```bash
# back up current config
sudo cp /etc/netplan/00-installer-config.yaml /etc/netplan/00-installer-config.yaml.dhcp.bak

# install the static config (from the repo dir)
sudo install -m 600 00-installer-config.static.yaml /etc/netplan/00-installer-config.yaml

# validate + apply with auto-revert (must be interactive: ssh -t mini)
sudo netplan generate
sudo netplan try --timeout 120     # applies; press ENTER within 120s to KEEP, else auto-reverts

# verify in a SECOND terminal / fresh connection BEFORE pressing Enter:
ip -4 route show default                 # default via 192.168.10.1 dev enp3s0f0
ping -c2 192.168.10.1                     # gateway reachable
resolvectl query home.tabaska.us         # DNS still works
# from another host:  ssh mini 'echo ok'  &&  dig @192.168.10.2 +short home.tabaska.us
```

If all green, press **Enter** to commit. If anything is wrong, do nothing — `netplan try` auto-reverts to DHCP in 120s.

### Rollback

```bash
sudo cp /etc/netplan/00-installer-config.yaml.dhcp.bak /etc/netplan/00-installer-config.yaml
sudo netplan apply
```

(Or restore the timestamped `*.pre-static-*` backup that `apply-static-ip.sh` wrote.)

## The `net-selfheal` watchdog (permanent backstop)

Even under static IP, `net-selfheal` stays deployed. Its `networkctl renew` step becomes a no-op, but the **link-bounce / networkd-restart** escalation still recovers generic link faults.

### `net-selfheal.service`

```ini
[Unit]
Description=Self-heal enp3s0f0 when its DHCP lease/route is lost
Documentation=file://.../foss-setup/docs/handoff-rollout-state.md
After=network.target systemd-networkd.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/net-selfheal.sh
TimeoutStartSec=90
```

### `net-selfheal.timer`

```ini
[Unit]
Description=Run net-selfheal every minute (recover NIC after DHCP lease loss)

[Timer]
OnBootSec=90
OnUnitActiveSec=60
AccuracySec=10s

[Install]
WantedBy=timers.target
```

Fires 90s after boot then every 60s.

### `/usr/local/sbin/net-selfheal.sh` (behavior)

`set -uo pipefail`; `IF=enp3s0f0`, `GW=192.168.10.1`; logs every step to the journal under tag `net-selfheal` (query with `journalctl -t net-selfheal`).

- **`healthy()`** = default route is `via 192.168.10.1 dev enp3s0f0` **and** the gateway pings (up to 3 tries). If healthy → `exit 0` (no-op).
- Otherwise it logs the unhealthy route/addr snapshot and **escalates**:
  1. `step1: networkctl renew enp3s0f0`, sleep 5, re-check → "RECOVERED after renew".
  2. `step2: ip link set enp3s0f0 down/up` (down, sleep 2, up, sleep 2), `networkctl renew`, sleep 8, re-check → "RECOVERED after link bounce".
  3. `step3: systemctl restart systemd-networkd`, sleep 8, re-check → "RECOVERED after networkd restart".
  4. Still down → logs `STILL DOWN after all steps` with a `networkctl status` diagnostic dump and `exit 1` (so the next incident is fully captured).

## `KeepConfiguration=dhcp` drop-in

Deployed 2026-07-09 as the first backstop. Live at `/etc/systemd/network/10-netplan-enp3s0f0.network.d/10-keepconfiguration.conf`:

```ini
[Network]
# Keep DHCP address+routes if the lease cannot be renewed (root-cause fix
# for recurring off-network outages, 2026-07-09). Backstopped by net-selfheal.timer.
KeepConfiguration=dhcp
```

This is **DHCP-only** and therefore moot now that mini is static. README step 5b says to tidy it up after static is confirmed:

```bash
sudo rm -f /etc/systemd/network/10-netplan-enp3s0f0.network.d/10-keepconfiguration.conf
sudo networkctl reload
```

!!! note "Validated against live mini (2026-07-14)"
    The KeepConfiguration drop-in is **still present** — README step 5b (remove it) has not been done. It is harmless under static IP; removal is cosmetic tidy-up, not required.

## Open follow-ups

- **README step 5b** — remove the now-moot `10-keepconfiguration.conf` drop-in (cosmetic, see note above).
- **Ansible** — fold the static netplan config + the `net-selfheal` units into the ansible **mini** role so a reprovision keeps them (currently applied out-of-band, not reproducible from ansible).
- **UniFi (secondary, now moot)** — investigate why the controller wasn't honoring in-lease RENEW/REBIND for MAC `98:5a:eb:ca:b2:ef`. Static makes this a non-issue but it may bite other DHCP clients.

## Quick health checks

```bash
# unit state
ssh mini "systemctl status net-selfheal.timer apply-static-ip.service apply-static-ip.timer --no-pager"
ssh mini "systemctl is-enabled net-selfheal.timer apply-static-ip.timer"   # expect: enabled / disabled

# addressing (expect static .2, dhcp4:false)
ssh mini "ip -4 addr show enp3s0f0; ip -4 route show default"
ssh mini "cat /etc/netplan/00-installer-config.yaml"

# watchdog activity (empty journal = healthy no-op)
ssh mini "journalctl -t net-selfheal --no-pager -n 20"
ssh mini "cat /var/log/apply-static-ip.log"
```

---

[← Host internals reference](index.md)
