# Firewall policy order

> The authoritative ordered list of UniFi Zone-Based Firewall (ZBF) policies for the homelab, plus the phased order in which to add them.
_Source: `foss-setup/configs/network/firewall-policy-order.md` · migrated + validated 2026-07-14._

UniFi Network 9.x evaluates policies top-down within the zone matrix; **more specific
allow policies must sit ABOVE broader block policies**. Built-in policies (return
traffic, gateway services) exist already — the list below is what you add/confirm.

The zones and subnets referenced here are the real, deployed ones on the UniFi Dream
Wall (six gateway SVIs — `192.168.{1,10,20,30,40,50}.1` — all confirmed reachable
2026-07-14): Internal/mgmt (VLAN 1), Trusted (10), IoT (20), Cameras (30), Work (40),
Guest/Hotspot (50), plus the predefined External and Gateway zones.

!!! note "Version note"
    The exact live UniFi Network minor version is not machine-audited (the operator
    keeps the controller/router off the fleet-SSH surface). The UI paths below are from
    Ubiquiti's help center and match the sibling walkthrough doc; confirm the path for
    your installed minor before clicking.

UI path by version (Ubiquiti help center):

- **Network 9.4+:** Settings → Zones → *Create Policy* (or Settings → Policy Table → *Create New Policy*)
- **Network 9.3:** Settings → Policy Engine → Zones → *Create Policy*
- Reference: https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi

!!! tip
    Give every policy a **description** (9.x supports it) so future-you knows why.
    Leave **Auto Allow Return Traffic** ON for client-initiated allows.

## Order of operations

1. **Phase A — Confirm gateway access first.** Verify (or create) `<each internal zone> →
   Gateway: Allow` for DHCP/DNS/NTP (policies **5–9**). If you block this, clients lose
   DNS/IP. (Often a built-in.)
2. **Phase B — Add specific allows** (policies **1–4, 10–13**; higher priority).
3. **Phase C — Add broad blocks** (policies **14–19**; lower priority).
4. **Phase D — Reorder, delete ZBF migration duplicates, verify** by running
   `scripts/network/zbf-isolation-verify.sh` from each VLAN.
5. Confirm each internal zone has **→ External: Allow** where intended (Cameras = Block).

## Policy list (top = highest priority)

Phases: **A** = Gateway (#5–9) · **B** = allows (#1–4, #10–13) · **C** = blocks (#14–19)

| # | Phase | Description | Source | Destination | Match (port/app) | Action | Return |
|---|---|---|---|---|---|---|---|
| 1 | B | Mgmt full access | Internal (mgmt) | *each zone* (see note) | any | Allow | auto |
| 2 | B | Trusted → IoT control (cast/Hue/Nest/Midea) | Trusted | IoT | any (or scope to needed ports) | Allow | auto |
| 3 | B | Trusted → Cameras (view/NVR) | Trusted | Cameras | TCP 80/443/554 (RTSP) + vendor app ports | Allow | auto |
| 4 | B | mDNS reflect Trusted↔IoT (control ports) | Trusted | IoT | AirPlay/Cast/HomeKit service ports | Allow | auto |
| 5 | A | Trusted → Gateway (DNS/DHCP/NTP) | Trusted | Gateway | UDP 53/67/123, TCP 53 | Allow | auto |
| 6 | A | IoT → Gateway (DNS/DHCP/NTP) | IoT | Gateway | UDP 53/67/123 | Allow | auto |
| 7 | A | Cameras → Gateway (DHCP/NTP only) | Cameras | Gateway | UDP 67/123 | Allow | auto |
| 8 | A | Work → Gateway (DNS/DHCP) | Work | Gateway | UDP 53/67, TCP 53 | Allow | auto |
| 9 | A | Guest → Gateway (DNS/DHCP) | Hotspot | Gateway | UDP 53/67, TCP 53 | Allow | auto |
| 10 | B | Trusted → Internet | Trusted | External | any | Allow | auto |
| 11 | B | IoT → Internet | IoT | External | any (optionally block, or filter) | Allow | auto |
| 12 | B | Work → Internet | Work | External | any | Allow | auto |
| 13 | B | Guest → Internet | Hotspot | External | any | Allow | auto |
| 14 | C | **Block Cameras → Internet** | Cameras | External | any | Block | — |
| 14b | C | **Block IoT → Gateway admin** (router console) | IoT | Gateway | TCP 22/80/443 (HTTP/HTTPS/SSH) | Block | — |
| 15 | C | **Block IoT → Trusted** | IoT | Trusted | any | Block | — |
| 16 | C | **Block IoT → Internal/Cameras/Work** | IoT | Internal, Cameras, Work | any | Block | — |
| 17 | C | **Block Cameras → all internal** | Cameras | Trusted, IoT, Work, Internal | any | Block | — |
| 18 | C | **Block Work → all internal** | Work | Trusted, IoT, Cameras, Internal | any | Block | — |
| 19 | C | **Block Guest → all internal** | Hotspot | any internal zone | any | Block | — |

Notes:

- **#1 Mgmt full access:** UniFi has no "Destination: Any" zone. Create one Allow policy
  per destination zone (Internal, Trusted, IoT, Cameras, Work, Hotspot, Gateway, External).
  Set Source IP and Dest IP/network to **Any**; the Destination Zone dropdown defaults to
  External — change it for each policy.
- Rule **14b** stops a compromised IoT device from reaching the router's admin console.
  Keep it **above** the broad IoT allows and below the scoped `IoT → Gateway` DNS/DHCP/NTP
  allow (#6) — different ports, so they don't conflict; it's defense-in-depth over the
  implicit default-deny.
- Rules 15–19 are the isolation backbone. Because UniFi is **stateful**, blocking
  `IoT → Trusted` does NOT break `Trusted → IoT` sessions (return traffic auto-allowed).
- If you use the **Guest/Hotspot network type**, much of #19 is enforced automatically —
  keep the explicit block as defense-in-depth.
- Scope rules 2–4 to ports rather than blanket `any` once things work, to shrink the
  attack surface.

## Post-migration sanity check

Automated legacy→ZBF conversion can create **redundant/overlapping** policies. After
enabling ZBF, review the generated list and delete duplicates. (Ubiquiti + multiple
practitioner guides call this out.) ZBF migration is a one-way door — back up the config
first (Settings → System → Backups → Download → *Settings Only*).

## Authoritative docs

- Zone-Based Firewalls in UniFi — https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi
- UniFi Network 9.0 (ZBF overview) — https://blog.ui.com/article/unifi-network-9-0-built-to-scale

---
[← Network reference](index.md)
