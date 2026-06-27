# UniFi Dream Wall — VLAN / Zone / Firewall Plan

Target: **5 networks, not over-segmented.** Gaming/streaming stays on **Trusted**
(Moonlight/Sunshine discover each other via mDNS on the *same* subnet — a separate
gaming VLAN forces a router hop and breaks auto-discovery). UniFi Network 9.x uses a
**Zone-Based Firewall (ZBF)**; networks (VLANs) are assigned to zones and policies
control traffic *between* zones.

> ZBF migration is a **one-way door** — back up the config first
> (Settings → System → Backups → Download → *Settings Only*).

## Networks (VLANs)

| Network (VLAN) | VLAN ID | Subnet (example) | DHCP | mDNS proxy | Notes |
|---|---|---|---|---|---|
| Default (mgmt) | 1 | 192.168.1.0/24 | Yes | Off | UniFi gear only — gateway, switches, APs. No clients. |
| Trusted | 10 | 192.168.10.0/24 | Yes | On | PCs, NAS, Mac mini, phones, consoles, **Sunshine host + Moonlight clients**, Home Assistant |
| IoT | 20 | 192.168.20.0/24 | Yes | On | Hue bridge, Nest, Midea AC/dehumidifier, smart TVs / streaming sticks |
| Cameras (optional) | 30 | 192.168.30.0/24 | Yes | Off | IP cameras — most locked down, no internet |
| Work | 40 | 192.168.40.0/24 | Yes | Off | Work laptop — internet only, no LAN access |
| Guest | 50 | 192.168.50.0/24 | Yes | Off | Visitors — use the **Guest/Hotspot** network type for built-in isolation |

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

- Moonlight discovers the Sunshine host via mDNS **on the same subnet** → keep both on
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
