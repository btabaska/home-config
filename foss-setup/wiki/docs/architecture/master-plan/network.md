# 1. The home network: segmenting the UniFi Dream Wall

The Dream Wall is the all-in-one core (router + firewall + a 17-port GbE switch with 12 PoE ports + 2× 10G SFP+, split one LAN / one WAN + WiFi 6 + the Network controller), so everything hangs off it. Goal: isolate the risky stuff (IoT, guests, work laptop) without over-engineering — which kills both sanity and, via mDNS headaches, the smart home.

> **Status (validated 2026-07-13/14):** segmentation is **implemented and live** — all six gateway SVIs answer (`192.168.{1,10,20,30,40,50}.1` → Default/Trusted/IoT/Cameras/Work/Guest). Trusted = `192.168.10.0/24` (managed hosts); IoT = `192.168.20.0/24` (Hue `.20.100`); **Trusted → IoT allow verified** (Hue reachable). The operator confirmed the subnets + zone-firewall rules but **declined UniFi controller/SSH access**, so router-internal specifics (exact ZBF policy order, per-VLAN mDNS-proxy toggles, IGMP-snooping state) are **operator-confirmed only**, not machine-audited.

## The honest answer on "how many networks"

Resist the urge to build a VLAN per use case. IoT is just another internal VLAN, and over-zoning multiplies the policy surface for no benefit. A separate gaming/streaming VLAN actively *hurts* — Moonlight discovers the Sunshine host via mDNS on the same subnet, so different VLANs force a router hop and break auto-discovery. **~4-5 networks, and gaming/streaming stays on the trusted network with QoS, not its own VLAN.**

## The layout

```
Fiber  ->  ISP ONT (bridge mode)  ->  UniFi Dream Wall  ->  [downstream switches / APs]  ->  devices
                                          (router + firewall + switch + WiFi6 + controller)
```

UniFi's Zone-Based Firewall ships with six built-in zones — **Internal, External, Gateway, VPN, Hotspot, DMZ**. By default all LANs land in *Internal* and the WAN is *External*. For real segmentation you **create custom zones** and assign each network to one:

| Network (VLAN) | Firewall zone | What's on it |
|---|---|---|
| Default (mgmt) | Internal | UniFi gear only — gateway, switches, APs. No clients. |
| Trusted | Trusted | PCs, NAS, Mac mini, phones, consoles, **Home Assistant (HA Green)**, **Sunshine host + Moonlight clients** |
| IoT | IoT (untrusted) | Hue bridge, Nest, Midea AC/dehumidifier, smart TVs / streaming sticks |
| Cameras (optional) | Cameras (untrusted) | Any IP cameras — most locked down, no internet |
| Work | Work | Work laptop — internet only, no access to other VLANs |
| Guest | Hotspot | Visitors — isolated, client isolation on |

Home Assistant lives on **Trusted**, not IoT. **Prefer keeping HA single-homed** and putting any Matter devices on HA's own VLAN; dual-homing HA across two NICs works but widens HA's exposure. It reaches IoT devices because Trusted → IoT is allowed.

## Firewall rules that actually isolate (UniFi Network 9.x = Zone-Based Firewall)

**Back up your config first — migrating to the Zone-Based Firewall is a one-way door** and can sever VPNs, mDNS, and inter-VLAN flows if you rush it.

The model: **allow Trusted → Untrusted (return traffic is automatic — stateful firewalls need no "allow established/related" rule); block Untrusted → Trusted; add narrow pinholes for the few flows that must cross.** For the IoT VLAN:

- Allow IoT → internet, and allow IoT → gateway for DNS 53, DHCP 67, NTP 123. **Never blanket-block the gateway** or devices can't get an IP, resolve names, or sync time.
- Block IoT → RFC1918 (10/8, 172.16/12, 192.168/16) so it can't reach other subnets.
- Block IoT → gateway admin (HTTP/HTTPS/SSH) so a compromised device can't touch the router console.
- **Order matters:** specific allows above the broad block; UniFi custom policies outrank built-ins — use Reorder. Rules are **directional**.
- **Work VLAN:** internet-only; block → all other VLANs.
- **Guest:** UniFi's built-in Guest network type (auto-isolation) + Client Device Isolation.

## Don't break casting and your smart home (mDNS)

HA, Chromecast, AirPlay, Matter, and Sonos all rely on mDNS/multicast, which doesn't cross VLANs by default. To keep discovery working between Trusted and IoT:

- Settings → Networks → **Multicast Settings: enable mDNS / IoT Auto Discovery** for those networks.
- **Turn IGMP Snooping OFF** — UniFi's implementation is aggressive and drops the discovery packets Apple TVs / HomePods / Matter devices depend on.
- **Matter caveat:** Matter uses link-local IPv6 multicast and is hard to isolate on a separate VLAN from HA. Current devices (Hue via Zigbee bridge, Nest and Midea over WiFi/IP) are fine on IoT. If later Matter devices misbehave across VLANs, put those on HA's VLAN.

> **Open follow-up (`#4` gate):** which VLAN the HomePods are on determines the HA↔HomeKit hub path — Trusted = native mDNS with HA; IoT = needs an mDNS proxy for `_hap._tcp.local` + IGMP off + a firewall allow. This is operator-UI + on-device work.

## Security & privacy extras

- **Enable IDS/IPS** (Threat Management) on the Dream Wall — it has the CPU. It can cap throughput at multi-gig, but for typical use it's worth it.
- **Network-wide DNS filtering:** run **AdGuard Home** and point VLAN DHCP DNS at it. **Live:** AdGuard runs on both the mini and the NAS (`adguardhome-nas` confirmed).
- **Encrypt the DNS that leaves the house:** point AdGuard at **Unbound** (local recursive resolver + DNSSEC), or at minimum DoT/DoH to Quad9/Cloudflare.
- **Fail-open DNS chain:** DHCP lists **three** resolvers — primary AdGuard on the mini, **secondary AdGuard on the NAS** (independent DoT upstream), and **tertiary UniFi gateway** for bare internet when both filter boxes are down. A single-DNS deployment is a house-wide outage when the mini reboots (incident 2026-07-03). See `configs/network/dns-resilience-plan.md`.
  - **⚠️ Corrected:** the plan's *anti-bypass* step (NAT-redirect outbound :53 + block DoH) was **retired** (`dns-05`, 2026-07-14) — the NAT :53 redirect kills the gateway fallback, and the operator prefers AdGuard-down clients bypass to the gateway over a house-wide DNS blackhole (**fail-open by design**).
- Once Hue is fully local in HA, you can block the Hue bridge from the internet. (Nest needs Google's cloud; Midea can be made fully local with an ESPHome dongle — see [Smart home](smart-home.md).)
- Use WPA3 where supported; map one SSID each to Trusted, IoT, Guest, and Work.

## Speed

Performance comes from physics and tuning, not segmentation:

- **Wire what you can** — the rig, NAS, Mac mini, and any Moonlight client near the TV.
- WiFi 6 on the Dream Wall (6E/7 with newer APs); clean DFS channels, sensible widths, low SSID count.
- For local Moonlight/Sunshine, same-VLAN + wired = effectively zero added latency. Reach for QoS / Smart Queues only if you see contention.

---
[← index](index.md)
