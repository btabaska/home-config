# Firewall policy checklist

> Tick-box guide for creating the UniFi zone-based firewall (ZBF) policies on the Dream Wall (net-05).

_Source: `foss-setup/configs/network/firewall-policy-checklist.md` · migrated + validated 2026-07-14._

**Open:** Settings → Zones → **Create Policy** (or Policy Table → Create New Policy)

Companion docs in the repo: `foss-setup/configs/network/firewall-policy-order.md`, `firewall-policy-walkthrough.md`, `vlan-zone-firewall-plan.md`.

---

## Before you start

- [ ] Back up: Settings → System → Backups → Download → **Settings Only**
- [ ] net-04 done: each VLAN assigned to the correct zone
- [ ] Policies are evaluated **top to bottom** — drag yours above **Allow All Traffic**

The subnet scheme these policies assume (validated live: gateway `192.168.10.1` reachable, HA at `192.168.10.50` returns 200):

| Zone | VLAN | Subnet |
|---|---|---|
| Default (mgmt / Internal) | 1 | `192.168.1.0/24` |
| Trusted | 10 | `192.168.10.0/24` (all managed hosts; HA `.50`) |
| IoT | 20 | `192.168.20.0/24` (Hue bridge `.20.100`) |
| Cameras | 30 | `192.168.30.0/24` |
| Work | 40 | `192.168.40.0/24` |
| Guest / Hotspot | 50 | `192.168.50.0/24` |

---

## UniFi UI — field reference

These are the controls you see when creating a policy:

| UI section | Control | Options |
|---|---|---|
| **Name** | free text | Short label (copy from each policy below) |
| **Source Zone** | dropdown | Internal, External, Gateway, Trusted, IoT, Cameras, Work, Hotspot, … |
| **Source** (below zone) | dropdown | Any · Device · Network · IP · MAC · Identity |
| **Source Port** | dropdown | Any · Specific · List |
| **Action** | dropdown | Block · **Allow** · Reject |
| **Action** | checkbox | **Auto allow return traffic** |
| **Destination Zone** | dropdown | *(defaults to Internal — change every time)* |
| **Destination** (below zone) | dropdown | Any · App · IP · Domain · Region |
| **Destination Port** | dropdown | Any · Specific · List |
| **IP Version** | dropdown | Both · IPv4 · IPv6 |
| **Protocol** | dropdown | All · TCP/UDP · TCP · UDP · Custom |
| **Connection State** | dropdown | **All** · Return Traffic · Custom |
| **Connection State** | checkboxes | Match IPsec · Syslog logging |
| **Schedule** | dropdown | **Always** · Daily · Weekly · One Time · Custom |
| **Description** | free text | Why this rule exists (copy from below) |

### Defaults used on almost every policy

Unless a policy row says otherwise, always set:

| Field | Value |
|---|---|
| Source (2nd dropdown) | **Any** |
| Source Port | **Any** |
| Destination (2nd dropdown) | **Any** |
| IP Version | **Both** |
| Connection State | **All** *(not "Return Traffic" — built-in handles that)* |
| Match IPsec | **unchecked** |
| Syslog logging | **unchecked** *(optional: enable later)* |
| Schedule | **Always** |

### Allow vs Block

| Policy type | Action | Auto allow return traffic |
|---|---|---|
| **Allow** rules | Allow | **checked ✓** |
| **Block** rules | Block | **unchecked** |

### Port fields

| When protocol is… | Destination Port |
|---|---|
| **All** | **Any** |
| **TCP** or **UDP** or **TCP/UDP** with specific ports | **List** → enter port numbers (e.g. `53`, `67`, `123`) |

If **List** is not available, use **Specific** and create one policy per port.

---

## Built-ins — do NOT delete

Keep: Allow Return Traffic · Allow mDNS · Allow DHCP · Allow DNS · Hotspot rules ·
Port Forward Plex/Warcraft · Masquerade NAT · **Allow All Traffic** (below your rules) ·
**Block All Traffic** (bottom).

---

## Part 1 — Create each policy

Check the box when saved. Only fields **different from defaults** are called out in
bold; everything else use the defaults table above.

---

### #1 Mgmt full access (8 policies)

Create **one policy per row**. Only **Name**, **Destination Zone**, and **Description**
change between them.

- [ ] **#1a** · - [ ] **#1b** · - [ ] **#1c** · - [ ] **#1d** · - [ ] **#1e** · - [ ] **#1f** · - [ ] **#1g** · - [ ] **#1h**

| Field | Value (same for all 8 except Destination Zone) |
|---|---|
| **Name** | `Mgmt Internal to <DestZone>` *(e.g. `Mgmt Internal to Trusted`)* |
| **Source Zone** | **Internal** |
| **Source** | Any |
| **Source Port** | Any |
| **Action** | **Allow** |
| **Auto allow return traffic** | **✓ checked** |
| **Destination Zone** | **see table ↓** |
| **Destination** | Any |
| **Destination Port** | Any |
| **IP Version** | Both |
| **Protocol** | **All** |
| **Connection State** | All |
| **Schedule** | Always |
| **Description** | Mgmt VLAN full access to all zones for UniFi administration |

| Policy | Destination Zone |
|---|---|
| #1a | **Internal** |
| #1b | **Trusted** |
| #1c | **IoT** |
| #1d | **Cameras** |
| #1e | **Work** |
| #1f | **Hotspot** |
| #1g | **Gateway** |
| #1h | **External** |

---

### #2 Trusted → IoT control

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Trusted to IoT control` |
| **Source Zone** | **Trusted** |
| **Source** | Any |
| **Source Port** | Any |
| **Action** | **Allow** |
| **Auto allow return traffic** | **✓ checked** |
| **Destination Zone** | **IoT** |
| **Destination** | Any |
| **Destination Port** | Any |
| **IP Version** | Both |
| **Protocol** | **All** |
| **Connection State** | All |
| **Schedule** | Always |
| **Description** | Phone/HA on Trusted controls Hue/Nest/Midea and casts to IoT devices |

---

### #3 Trusted → Cameras view/NVR

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Trusted to Cameras view NVR` |
| **Source Zone** | **Trusted** |
| **Source** | Any |
| **Source Port** | Any |
| **Action** | **Allow** |
| **Auto allow return traffic** | **✓ checked** |
| **Destination Zone** | **Cameras** |
| **Destination** | Any |
| **Destination Port** | **List** → `80`, `443`, `554` |
| **IP Version** | Both |
| **Protocol** | **TCP** |
| **Connection State** | All |
| **Schedule** | Always |
| **Description** | View cameras and RTSP streams from Trusted (NVR/Protect app) |

---

### #4 mDNS Trusted→IoT control *(optional — skip until casting fails)*

- [ ] Created · - [ ] Skipped

| Field | Value |
|---|---|
| **Name** | `Trusted to IoT mDNS control` |
| **Source Zone** | **Trusted** |
| **Source** | Any |
| **Source Port** | Any |
| **Action** | **Allow** |
| **Auto allow return traffic** | **✓ checked** |
| **Destination Zone** | **IoT** |
| **Destination** | Any |
| **Destination Port** | **Any** *(or List common cast ports — see `mdns-multicast-checklist.md`)* |
| **IP Version** | Both |
| **Protocol** | **TCP/UDP** |
| **Connection State** | All |
| **Schedule** | Always |
| **Description** | Unicast control traffic after mDNS discovery (AirPlay/Cast/HomeKit) |

---

### #5 Trusted → Gateway DNS/DHCP/NTP

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Trusted to Gateway DNS DHCP NTP` |
| **Source Zone** | **Trusted** |
| **Source** | Any |
| **Source Port** | Any |
| **Action** | **Allow** |
| **Auto allow return traffic** | **✓ checked** |
| **Destination Zone** | **Gateway** |
| **Destination** | Any |
| **Destination Port** | **List** → `53`, `67`, `123` |
| **IP Version** | Both |
| **Protocol** | **TCP/UDP** |
| **Connection State** | All |
| **Schedule** | Always |
| **Description** | Trusted clients need DHCP (67), DNS (53), NTP (123) from gateway |

*If List fails with TCP/UDP, split into three policies: UDP 67, UDP 123, TCP/UDP 53.*

---

### #6 IoT → Gateway DNS/DHCP/NTP

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `IoT to Gateway DNS DHCP NTP` |
| **Source Zone** | **IoT** |
| **Source** | Any |
| **Source Port** | Any |
| **Action** | **Allow** |
| **Auto allow return traffic** | **✓ checked** |
| **Destination Zone** | **Gateway** |
| **Destination** | Any |
| **Destination Port** | **List** → `53`, `67`, `123` |
| **IP Version** | Both |
| **Protocol** | **UDP** *(add separate TCP policy for port 53 if needed)* |
| **Connection State** | All |
| **Schedule** | Always |
| **Description** | IoT devices need DHCP, DNS, NTP from gateway |

---

### #7 Cameras → Gateway DHCP/NTP

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Cameras to Gateway DHCP NTP` |
| **Source Zone** | **Cameras** |
| **Source** | Any |
| **Source Port** | Any |
| **Action** | **Allow** |
| **Auto allow return traffic** | **✓ checked** |
| **Destination Zone** | **Gateway** |
| **Destination** | Any |
| **Destination Port** | **List** → `67`, `123` |
| **IP Version** | Both |
| **Protocol** | **UDP** |
| **Connection State** | All |
| **Schedule** | Always |
| **Description** | Cameras need DHCP and NTP only — no DNS/internet |

---

### #8 Work → Gateway DNS/DHCP

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Work to Gateway DNS DHCP` |
| **Source Zone** | **Work** |
| **Source** | Any |
| **Source Port** | Any |
| **Action** | **Allow** |
| **Auto allow return traffic** | **✓ checked** |
| **Destination Zone** | **Gateway** |
| **Destination** | Any |
| **Destination Port** | **List** → `53`, `67` |
| **IP Version** | Both |
| **Protocol** | **TCP/UDP** |
| **Connection State** | All |
| **Schedule** | Always |
| **Description** | Work laptop needs DHCP and DNS from gateway |

---

### #9 Guest → Gateway DNS/DHCP/NTP

- [ ] Created · - [ ] Skipped *(if Hotspot built-in DHCP/DNS already covers Guest)*

| Field | Value |
|---|---|
| **Name** | `Guest to Gateway DNS DHCP NTP` |
| **Source Zone** | **Hotspot** |
| **Source** | Any |
| **Source Port** | Any |
| **Action** | **Allow** |
| **Auto allow return traffic** | **✓ checked** |
| **Destination Zone** | **Gateway** |
| **Destination** | Any |
| **Destination Port** | **List** → `53`, `67`, `123` |
| **IP Version** | Both |
| **Protocol** | **TCP/UDP** |
| **Connection State** | All |
| **Schedule** | Always |
| **Description** | Guest clients need DHCP, DNS, NTP from gateway |

---

### #10 Trusted → Internet

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Trusted to Internet` |
| **Source Zone** | **Trusted** |
| **Action** | **Allow** · Auto allow return traffic **✓** |
| **Destination Zone** | **External** |
| **Destination Port** | Any |
| **Protocol** | **All** · Connection State All · Schedule Always |
| **Description** | Trusted clients reach the internet |

---

### #11 IoT → Internet

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `IoT to Internet` |
| **Source Zone** | **IoT** |
| **Action** | **Allow** · Auto allow return traffic **✓** |
| **Destination Zone** | **External** |
| **Destination Port** | Any |
| **Protocol** | **All** · Connection State All · Schedule Always |
| **Description** | IoT devices reach the internet (Nest cloud, TV updates, etc.) |

---

### #12 Work → Internet

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Work to Internet` |
| **Source Zone** | **Work** |
| **Action** | **Allow** · Auto allow return traffic **✓** |
| **Destination Zone** | **External** |
| **Destination Port** | Any |
| **Protocol** | **All** · Connection State All · Schedule Always |
| **Description** | Work laptop internet-only access |

---

### #13 Guest → Internet

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Guest to Internet` |
| **Source Zone** | **Hotspot** |
| **Action** | **Allow** · Auto allow return traffic **✓** |
| **Destination Zone** | **External** |
| **Destination Port** | Any |
| **Protocol** | **All** · Connection State All · Schedule Always |
| **Description** | Guest internet-only access |

**Do NOT create** Cameras → External allow.

---

### #14 Block Cameras → Internet

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Block Cameras to Internet` |
| **Source Zone** | **Cameras** |
| **Action** | **Block** · Auto allow return traffic **unchecked** |
| **Destination Zone** | **External** |
| **Destination Port** | Any |
| **Protocol** | **All** · Connection State All · Schedule Always |
| **Description** | Cameras must not reach the internet |

---

### #14b Block IoT → Gateway admin

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Block IoT to Gateway admin` |
| **Source Zone** | **IoT** |
| **Action** | **Block** · Auto allow return traffic **unchecked** |
| **Destination Zone** | **Gateway** |
| **Destination Port** | **List** → `22`, `80`, `443` |
| **Protocol** | **TCP** · Connection State All · Schedule Always |
| **Description** | Block compromised IoT from router SSH/HTTPS admin (DNS/DHCP on other ports still allowed by #6) |

---

### #15 Block IoT → Trusted

- [ ] Created

| Field | Value |
|---|---|
| **Name** | `Block IoT to Trusted` |
| **Source Zone** | **IoT** |
| **Action** | **Block** · Auto allow return traffic **unchecked** |
| **Destination Zone** | **Trusted** |
| **Destination Port** | Any |
| **Protocol** | **All** · Connection State All · Schedule Always |
| **Description** | IoT cannot initiate connections to Trusted (return traffic for Trusted→IoT still works) |

---

### #16 Block IoT → other internal zones

Same settings for each; only **Name**, **Destination Zone**, and **Description** change.
Source Zone **IoT**, Action **Block**, Auto allow return traffic **unchecked**, Protocol **All**, everything else default.

- [ ] **#16a** · - [ ] **#16b** · - [ ] **#16c**

| Policy | Name | Destination Zone | Description |
|---|---|---|---|
| #16a | `Block IoT to Internal mgmt` | **Internal** | IoT cannot reach mgmt VLAN |
| #16b | `Block IoT to Cameras` | **Cameras** | IoT cannot reach cameras |
| #16c | `Block IoT to Work` | **Work** | IoT cannot reach work laptop VLAN |

---

### #17 Block Cameras → all internal

Source Zone **Cameras**, Action **Block**, Auto allow return traffic **unchecked**, Protocol **All**, everything else default.

- [ ] **#17a** · - [ ] **#17b** · - [ ] **#17c** · - [ ] **#17d**

| Policy | Name | Destination Zone | Description |
|---|---|---|---|
| #17a | `Block Cameras to Trusted` | **Trusted** | Cameras cannot reach Trusted |
| #17b | `Block Cameras to IoT` | **IoT** | Cameras cannot reach IoT |
| #17c | `Block Cameras to Work` | **Work** | Cameras cannot reach Work |
| #17d | `Block Cameras to Internal mgmt` | **Internal** | Cameras cannot reach mgmt VLAN |

---

### #18 Block Work → all internal

Source Zone **Work**, Action **Block**, Auto allow return traffic **unchecked**, Protocol **All**, everything else default.

- [ ] **#18a** · - [ ] **#18b** · - [ ] **#18c** · - [ ] **#18d**

| Policy | Name | Destination Zone | Description |
|---|---|---|---|
| #18a | `Block Work to Trusted` | **Trusted** | Work laptop cannot reach Trusted |
| #18b | `Block Work to IoT` | **IoT** | Work laptop cannot reach IoT |
| #18c | `Block Work to Cameras` | **Cameras** | Work laptop cannot reach Cameras |
| #18d | `Block Work to Internal mgmt` | **Internal** | Work laptop cannot reach mgmt VLAN |

---

### #19 Block Guest → all internal

Source Zone **Hotspot**, Action **Block**, Auto allow return traffic **unchecked**, Protocol **All**, everything else default.

- [ ] **#19a** · - [ ] **#19b** · - [ ] **#19c** · - [ ] **#19d** · - [ ] **#19e**

| Policy | Name | Destination Zone | Description |
|---|---|---|---|
| #19a | `Block Guest to Internal mgmt` | **Internal** | Guest cannot reach mgmt VLAN |
| #19b | `Block Guest to Trusted` | **Trusted** | Guest cannot reach Trusted |
| #19c | `Block Guest to IoT` | **IoT** | Guest cannot reach IoT |
| #19d | `Block Guest to Cameras` | **Cameras** | Guest cannot reach Cameras |
| #19e | `Block Guest to Work` | **Work** | Guest cannot reach Work |

---

## Part 2 — Reorder (top → bottom)

- [ ] #1a–1h Mgmt allows
- [ ] #2 Trusted → IoT
- [ ] #3 Trusted → Cameras
- [ ] #4 mDNS *(if created)*
- [ ] #5–9 Gateway allows
- [ ] #10–13 Internet allows
- [ ] #14 · #14b · #15 · #16a–c · #17a–d · #18a–d · #19a–e blocks
- [ ] Built-ins (Return Traffic, mDNS, Hotspot, port forwards, …)
- [ ] Allow All Traffic
- [ ] Block All Traffic

---

## Part 3 — Verify

| From VLAN | Test | Expected |
|---|---|---|
| Trusted | Hue/Nest app / cast to TV | Works |
| IoT | `ping 192.168.10.1` | Fails |
| Cameras | `ping 8.8.8.8` | Fails |
| Work / Guest | Web works · ping Trusted fails | Pass |

Run the isolation-verify script from a client on the VLAN under test. It lives at
`foss-setup/scripts/network/zbf-isolation-verify.sh` and auto-detects the zone from the
`192.168.{vlan}.0/24` scheme, or you can set `ZONE=` explicitly:

```bash
# from foss-setup/scripts/network/
./zbf-isolation-verify.sh                                  # auto-detect zone
ZONE=iot  TRUSTED_IP=192.168.10.50 ./zbf-isolation-verify.sh
ZONE=work TRUSTED_IP=192.168.10.1  ./zbf-isolation-verify.sh
```

- [ ] All checks pass

---

## Stuck? Create these 3 first

### Mini #2 — Trusted → IoT

| Field | Value |
|---|---|
| Name | `Trusted to IoT control` |
| Source Zone | **Trusted** → Source: Any → Source Port: Any |
| Action | **Allow** · Auto allow return traffic **✓** |
| Destination Zone | **IoT** → Destination: Any → Destination Port: Any |
| IP Version | Both · Protocol: **All** · Connection State: **All** · Schedule: **Always** |

### Mini #6 — IoT → Gateway

| Field | Value |
|---|---|
| Name | `IoT to Gateway DNS DHCP NTP` |
| Source Zone | **IoT** → Source: Any → Source Port: Any |
| Action | **Allow** · Auto allow return traffic **✓** |
| Destination Zone | **Gateway** → Destination: Any → Destination Port: **List** `53`,`67`,`123` |
| IP Version | Both · Protocol: **UDP** · Connection State: **All** · Schedule: **Always** |

### Mini #15 — Block IoT → Trusted

| Field | Value |
|---|---|
| Name | `Block IoT to Trusted` |
| Source Zone | **IoT** → Source: Any → Source Port: Any |
| Action | **Block** · Auto allow return traffic **unchecked** |
| Destination Zone | **Trusted** → Destination: Any → Destination Port: Any |
| IP Version | Both · Protocol: **All** · Connection State: **All** · Schedule: **Always** |

Drag all three **above Allow All Traffic**, test, then continue with the full list.

---

## Policy count: ~38 total

| Category | Count |
|---|---|
| #1 Mgmt (1a–1h) | 8 |
| #2–4 pinholes | 2 required + 1 optional |
| #5–9 Gateway | 5 |
| #10–13 Internet | 4 |
| #14–19 blocks | 19 |
| **Total** | **~38** |

---
[← Network reference](index.md)
