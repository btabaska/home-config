# UniFi Dream Wall — VLAN / Zone / Firewall Plan

> **Re-audit 2026-07-13 (#15): implemented as designed.** The operator confirmed
> the subnets and zone-firewall rules below are deployed on the Dream Wall as
> directed, and declined controller/SSH access for an independent machine audit.
> Fleet-side corroboration (no router access): all **six** gateway SVIs answer —
> `192.168.{1,10,20,30,40,50}.1` all UP → Default/Trusted/IoT/Cameras/Work/Guest
> all exist; **Trusted = 192.168.10.0/24** (every managed host); **IoT =
> 192.168.20.0/24** (Hue bridge `.20.100`); **Trusted→IoT = Allow works** (Hue
> reachable from a Trusted host — now guarded by check `net-trusted-to-iot-reachable`).
> The example subnets below **are the real ones**. Zone-policy *internals* (exact
> rule order, `any`-scope leftovers), per-VLAN mDNS-proxy toggles, and IGMP-snooping
> state are operator-confirmed but not machine-verified here — see the #4/#16 gap
> list at the bottom.

Target: **5 networks, not over-segmented.** Gaming/streaming stays on **Trusted**
(Moonlight/Apollo discover each other via mDNS on the *same* subnet — a separate
gaming VLAN forces a router hop and breaks auto-discovery). UniFi Network 9.x uses a
**Zone-Based Firewall (ZBF)**; networks (VLANs) are assigned to zones and policies
control traffic *between* zones.

> ZBF migration is a **one-way door** — back up the config first
> (Settings → System → Backups → Download → *Settings Only*).

## Networks (VLANs)

Subnet column is **confirmed real** (2026-07-13 re-audit), not just illustrative —
each VLAN's gateway SVI answers at `192.168.<id>.1`.

| Network (VLAN) | VLAN ID | Subnet (confirmed) | DHCP | mDNS proxy | Notes |
|---|---|---|---|---|---|
| Default (mgmt) | 1 | 192.168.1.0/24 | Yes | Off | UniFi gear only — gateway, switches, APs. No clients. |
| Trusted | 10 | 192.168.10.0/24 ✅ | Yes | On | PCs, NAS, Mac mini, phones, consoles, **Apollo host + Moonlight clients**, Home Assistant (`.50`). All managed hosts live here. |
| IoT | 20 | 192.168.20.0/24 ✅ | Yes | On | Hue bridge (`.20.100` ✅), Nest, Midea AC/dehumidifier, smart TVs / streaming sticks |
| Cameras (optional) | 30 | 192.168.30.0/24 | Yes | Off | IP cameras — most locked down, no internet |
| Work | 40 | 192.168.40.0/24 | Yes | Off | Work laptop — internet only, no LAN access |
| Guest | 50 | 192.168.50.0/24 | Yes | Off | Visitors — use the **Guest/Hotspot** network type for built-in isolation |

_✅ = independently fleet-corroborated 2026-07-13. Others confirmed by the operator (router not machine-audited)._

VLAN IDs and subnets are conventions, not requirements (any 2–4094). Pick a scheme
where the third octet matches the VLAN ID for sanity (e.g. VLAN 20 → 192.168.20.0/24).

## Zones (group VLANs by trust level)

UniFi ships **six** predefined zones (**Internal, External, Gateway, VPN, Hotspot,
DMZ**) that cannot be deleted; you can add custom zones. (DMZ is unused in this
build — we have no public-facing servers to isolate there.) A minimal, sane mapping:

| Zone | Type | Networks assigned | Intent |
|---|---|---|---|
| Internal | predefined | Default (mgmt) | Management plane |
| Trusted | **custom** | Trusted (VLAN 10) | Full-trust clients |
| IoT | **custom** | IoT (VLAN 20) | Untrusted internal, internet-only |
| Cameras | **custom** | Cameras (VLAN 30) | Most locked down, usually no internet |
| Work | **custom** | Work (VLAN 40) | Internet-only, isolated from all LAN |
| Hotspot | predefined | Guest (VLAN 50) | Captive-portal guest isolation |
| External | predefined | WAN | The internet |
| Gateway | predefined | the UDW itself | DHCP/DNS/NTP to the gateway |

> Each network belongs to exactly one zone. Assign in
> Settings → Security → Zone-Based Firewall → Zones (path differs slightly by 9.x minor;
> see firewall-policy-order.md). Create policies per
> [firewall-policy-walkthrough.md](firewall-policy-walkthrough.md) (net-05).

## Zone matrix (intended traffic flows)

Rows = source, columns = destination. `A` = Allow, `B` = Block, `A*` = Allow specific
ports/services only, `↩` = stateful return traffic (auto-allowed).

| src ↓ \ dst → | Internal | Trusted | IoT | Cameras | Work | Hotspot | Gateway | External |
|---|---|---|---|---|---|---|---|---|
| **Internal (mgmt)** | A | A | A | A | A | A | A | A |
| **Trusted** | A* | A | A | A* | B | B | A | A |
| **IoT** | B | B (↩ only) | A | B | B | B | A* | A |
| **Cameras** | B | B (↩ only) | B | A | B | B | A* | B |
| **Work** | B | B | B | B | A | B | A* | A |
| **Hotspot (Guest)** | B | B | B | B | B | A | A* | A |

Key intents:
- **Trusted → IoT = Allow** so phones control Hue/Nest/Midea and cast to TVs.
- **IoT → Trusted = Block** (return traffic for Trusted-initiated sessions is auto-allowed).
- **Trusted → Cameras = Allow** (NVR/viewing); **Cameras → everything = Block** (incl. internet).
- **Work / Guest = internet only**, no lateral movement.
- Every internal zone needs **→ Gateway = Allow** for DHCP/DNS/NTP, or it breaks.

## mDNS / multicast (why gaming stays on Trusted)

- Moonlight discovers the Apollo host via mDNS **on the same subnet** → keep both on
  **Trusted**. No cross-VLAN proxy needed for game streaming.
- For cross-VLAN discovery you *do* want (e.g. phone on Trusted → Chromecast/AirPlay/HomeKit
  on IoT): enable the **Gateway mDNS Proxy on BOTH the source and destination VLANs**
  (enabling one side only is the #1 mistake), and add a narrowly-scoped firewall policy
  for the control ports. See `mdns-multicast-checklist.md`.
- Turn **IGMP snooping OFF** — UniFi's implementation is aggressive and drops the
  discovery packets Apple TVs / HomePods / Matter devices rely on (the #1 cause of
  "casting broke after segmentation"). It does not move multicast across VLANs anyway
  (that's the mDNS proxy's job); it only limits in-VLAN flooding, which is negligible at
  home scale. See `mdns-multicast-checklist.md`.

## Authoritative docs

- Zone-Based Firewalls in UniFi — https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi
- UniFi Network 9.0 announcement (ZBF) — https://blog.ui.com/article/unifi-network-9-0-built-to-scale
- UniFi Gateway mDNS Proxy — https://help.ui.com/hc/en-us/articles/12648701398807-UniFi-Gateway-Multicast-DNS-mDNS-Proxy

## Re-audit follow-ups (2026-07-13) — what's left, feeding #16 and #4

These need either the operator's UniFi UI or an on-device check (router not
machine-audited here):

**#16 — DNS tail (dns-03 / dns-04 / dns-05):**
- **dns-03 (DHCP fail-open chain on every client VLAN):** the chain
  `192.168.10.2 → .4 → .1` is applied on the Trusted host mini, but mini is now
  **statically** configured (`dhcp4: false` since 2026-07-10), so the fleet can't
  independently prove the *DHCP server* hands the chain to WiFi clients on
  Trusted/IoT/Guest/Work. Operator-confirmed only. To verify: UniFi → Settings →
  Networks → each client VLAN → DHCP → DNS Server = `192.168.10.2, 192.168.10.4,
  192.168.10.1` in that order. Resolvers themselves are guarded (`dns.yaml`).
- **dns-04 (verify script + outage runbook):** `scripts/network/dns-resilience-verify.sh`
  + `wiki/runbooks/dns-outage.md` exist — confirm they still match reality.
- **dns-05 (NAT :53 redirect + DoH block):** deferred by design until dns-03 is
  proven on all VLANs; do NOT enable before then (removes the gateway fallback).

**#4 — HomePod ↔ HA HomeKit hub (blocked on this audit):** HA (`.50`) + its
HomeKit Bridge are on **Trusted**; the gate is **which VLAN the HomePods are on**:
- HomePods on **Trusted** → same subnet as HA → mDNS (`_hap._tcp.local`) works
  natively, no proxy needed. Likely the quickest path.
- HomePods on **IoT** → need the **Gateway mDNS Proxy enabled on BOTH Trusted and
  IoT** for `_hap._tcp.local`, IGMP snooping **off**, and a firewall allow for the
  HAP control port (Trusted↔IoT). See `mdns-multicast-checklist.md`.
- **Need from operator for #4:** (a) which VLAN the HomePods sit on; (b) whether
  the Gateway mDNS proxy is enabled on the relevant VLAN(s); (c) IGMP-snooping
  state on those VLANs. Then #4 is an on-device Apple Home add-hub check.
