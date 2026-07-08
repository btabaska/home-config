# gateway — UniFi Dream Wall

Router, firewall, switch, WiFi 6, and the UniFi Network controller in one
box. Everything hangs off it.

| | |
|---|---|
| **Hardware** | UniFi Dream Wall — router + 17-port GbE switch (12 PoE) + 2× 10G SFP+ + WiFi 6 |
| **IP** | `192.168.10.1` |
| **Access** | **UniFi GUI only** — no useful CLI/API surface in this setup |
| **Power** | 24/7, ~30–40 W |

## What it does

- Routing, NAT, and the **Zone-Based Firewall** (custom zones: Trusted, IoT,
  Cameras, Work — see [Network](../network.md))
- VLANs and per-network **DHCP** — including the DNS chain handed to clients
  (`192.168.10.2, 192.168.10.4, 192.168.10.1`; pending: dns-03 done right)
- WiFi (one SSID each for Trusted, IoT, Guest, Work; WPA3 where possible)
- mDNS/IoT auto-discovery between Trusted and IoT (IGMP snooping OFF)
- IDS/IPS (Threat Management)
- **Tertiary DNS fallback** — bare internet resolution when both AdGuards are down

## Maintenance channel

**Human + GUI, always.** There is no config-as-code path; changes here are
the classic source of invisible drift, so the rule is: **every manual change
in the UniFi GUI gets one line in the handoff state doc**
(`foss-setup/docs/handoff-rollout-state.md`) — no exceptions. The 2026-07-07
audit found the DHCP DNS chain changed out-of-band and wrong; that rule
exists because of it.

## Backups

UniFi auto-backup is on by default; pull the `.unf` export into the repo
(`network/` in the control-repo layout) on a schedule. **Back up before any
zone/firewall migration — the Zone-Based Firewall migration is a one-way
door.**

## Failure blast radius

Gateway down = no routing, no DHCP, no WiFi, no inter-VLAN anything. Nothing
in this homelab mitigates that; it is the one true single point of failure.
