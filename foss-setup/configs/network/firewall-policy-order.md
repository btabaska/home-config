# UniFi ZBF — Firewall Policy List (in order)

UniFi Network 9.x evaluates policies top-down within the zone matrix; **more specific
allow policies must sit ABOVE broader block policies**. Built-in policies (return
traffic, gateway services) exist already — the list below is what you add/confirm.

UI path by version (Ubiquiti help center):
- **Network 9.4+:** Settings → Zones → *Create Policy* (or Settings → Policy Table → *Create New Policy*)
- **Network 9.3:** Settings → Policy Engine → Zones → *Create Policy*
- Reference: https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi

> Tip: give every policy a **description** (9.x supports it) so future-you knows why.
> Leave **Auto Allow Return Traffic** ON for client-initiated allows.

## Order of operations

1. **Confirm gateway access first.** Verify (or create) `<each internal zone> → Gateway:
   Allow` for DHCP/DNS/NTP. If you block this, clients lose DNS/IP. (Often a built-in.)
2. Add the **specific allows** below (higher priority).
3. Add the **broad blocks** below (lower priority).
4. Confirm each internal zone has **→ External: Allow** where intended (Cameras = Block).

## Policy list (top = highest priority)

| # | Description | Source | Destination | Match (port/app) | Action | Return |
|---|---|---|---|---|---|---|
| 1 | Mgmt full access | Internal (mgmt) | Any | any | Allow | auto |
| 2 | Trusted → IoT control (cast/Hue/Nest/Midea) | Trusted | IoT | any (or scope to needed ports) | Allow | auto |
| 3 | Trusted → Cameras (view/NVR) | Trusted | Cameras | TCP 80/443/554 (RTSP) + vendor app ports | Allow | auto |
| 4 | mDNS reflect Trusted↔IoT (control ports) | Trusted | IoT | AirPlay/Cast/HomeKit service ports | Allow | auto |
| 5 | Trusted → Gateway (DNS/DHCP/NTP) | Trusted | Gateway | UDP 53/67/123, TCP 53 | Allow | auto |
| 6 | IoT → Gateway (DNS/DHCP/NTP) | IoT | Gateway | UDP 53/67/123 | Allow | auto |
| 7 | Cameras → Gateway (DHCP/NTP only) | Cameras | Gateway | UDP 67/123 | Allow | auto |
| 8 | Work → Gateway (DNS/DHCP) | Work | Gateway | UDP 53/67, TCP 53 | Allow | auto |
| 9 | Guest → Gateway (DNS/DHCP) | Hotspot | Gateway | UDP 53/67, TCP 53 | Allow | auto |
| 10 | Trusted → Internet | Trusted | External | any | Allow | auto |
| 11 | IoT → Internet | IoT | External | any (optionally block, or filter) | Allow | auto |
| 12 | Work → Internet | Work | External | any | Allow | auto |
| 13 | Guest → Internet | Hotspot | External | any | Allow | auto |
| 14 | **Block Cameras → Internet** | Cameras | External | any | Block | — |
| 15 | **Block IoT → Trusted** | IoT | Trusted | any | Block | — |
| 16 | **Block IoT → Internal/Cameras/Work** | IoT | Internal, Cameras, Work | any | Block | — |
| 17 | **Block Cameras → all internal** | Cameras | Trusted, IoT, Work, Internal | any | Block | — |
| 18 | **Block Work → all internal** | Work | Trusted, IoT, Cameras, Internal | any | Block | — |
| 19 | **Block Guest → all internal** | Hotspot | any internal zone | any | Block | — |

Notes:
- Rules 15–19 are the isolation backbone. Because UniFi is **stateful**, blocking
  `IoT → Trusted` does NOT break `Trusted → IoT` sessions (return traffic auto-allowed).
- If you use the **Guest/Hotspot network type**, much of #19 is enforced automatically —
  keep the explicit block as defense-in-depth.
- Scope rules 2–4 to ports rather than blanket `any` once things work, to shrink the
  attack surface.

## Post-migration sanity check

Automated legacy→ZBF conversion can create **redundant/overlapping** policies. After
enabling ZBF, review the generated list and delete duplicates. (Ubiquiti + multiple
practitioner guides call this out.)

## Authoritative docs

- Zone-Based Firewalls in UniFi — https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi
- UniFi Network 9.0 (ZBF overview) — https://blog.ui.com/article/unifi-network-9-0-built-to-scale
