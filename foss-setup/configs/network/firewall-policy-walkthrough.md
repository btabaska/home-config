# UniFi ZBF — Firewall Policy Walkthrough (net-05)

Step-by-step guide for creating firewall policies on the Dream Wall. The authoritative
policy table lives in [firewall-policy-order.md](firewall-policy-order.md); zone/VLAN
mapping is in [vlan-zone-firewall-plan.md](vlan-zone-firewall-plan.md).

**Done when:** Trusted reaches IoT; IoT cannot ping Trusted; Cameras have no internet;
Work/Guest reach only the internet.

Run verification after Phase D:

```bash
# From a device on each VLAN (or set ZONE= explicitly):
./scripts/network/zbf-isolation-verify.sh
```

---

## Part 1 — Concepts (read before touching the UI)

### What is Zone-Based Firewall?

Instead of writing rules like "block 192.168.20.x → 192.168.10.x", UniFi groups VLANs
into **zones** and you write rules between zones. Each network (VLAN) belongs to exactly
one zone (assigned in net-04). This step defines **what traffic is allowed between zones**.

### The four special zones you cannot delete

| Zone | What it is | Why it matters |
|---|---|---|
| **Gateway** | The Dream Wall itself (192.168.x.1) | Clients need this for DHCP, DNS, NTP |
| **External** | WAN / the internet | Where "internet access" rules point |
| **Internal** | Your mgmt VLAN (Default) | Full admin access to everything |
| **Hotspot** | Guest network type | Built-in guest isolation (add explicit blocks as backup) |

Your **custom zones** (Trusted, IoT, Cameras, Work) hold the actual client VLANs.

### Gateway access is non-negotiable

Every client VLAN must reach **Gateway** for:

- **UDP 67** — DHCP (without this, devices never get an IP)
- **UDP/TCP 53** — DNS (without this, nothing resolves)
- **UDP 123** — NTP (time sync; optional but recommended)

If you block `IoT → Gateway`, every IoT device breaks — not because of isolation, but
because it can't get an IP or resolve names. **Always confirm Gateway allows before adding
blocks.** Cameras only need DHCP + NTP (no DNS if they don't browse the internet).

### Order matters (top wins)

UniFi evaluates policies **top to bottom**. The first matching rule wins.

```
Policy list (top = checked first)
┌─────────────────────────────────────┐
│ 1. Trusted → IoT        ALLOW  ← specific, high priority
│ 2. Trusted → Cameras    ALLOW
│ 3. Trusted → Internet   ALLOW
│ ...
│ 14. IoT → Trusted       BLOCK  ← broad, low priority
│ 15. Cameras → External  BLOCK
└─────────────────────────────────────┘
```

Allows for Gateway and specific cross-zone flows go **above** broad blocks. If you put a
broad `IoT → any BLOCK` above `IoT → Gateway ALLOW`, IoT devices lose DNS/IP.

### Stateful firewalls + "Auto Allow Return Traffic"

When your **phone on Trusted** opens a connection to a **Hue bridge on IoT**:

1. Phone initiates: `Trusted → IoT` (outbound)
2. Hue bridge replies: `IoT → Trusted` (return traffic)

You create an explicit **Allow** for `Trusted → IoT` and an explicit **Block** for
`IoT → Trusted`. These do not conflict because:

- The Allow matches the phone's *new* outbound request
- The Block stops an IoT device from *starting* a new connection to Trusted
- **Auto Allow Return Traffic** (keep ON) lets the Hue bridge's reply through automatically

**You do NOT need a separate "allow established" rule.**

### The three layers of your policy list

1. **Foundation (Gateway)** — policies 5–9: each zone → Gateway for DHCP/DNS/NTP
2. **Pinholes (specific allows)** — policies 1–4, 10–13: cross-zone and internet flows
3. **Isolation (broad blocks)** — policies 14–19: lock down untrusted zones

### What each zone should end up with

| Zone | Can reach | Cannot reach |
|---|---|---|
| **Trusted** | IoT (control), Cameras (view), Gateway, Internet | Work, Guest (by default) |
| **IoT** | Gateway (DNS/DHCP only), Internet | Trusted, Cameras, Work, Guest, router admin UI |
| **Cameras** | Gateway (DHCP/NTP only) | Everything else including internet |
| **Work** | Gateway, Internet | All internal zones |
| **Guest (Hotspot)** | Gateway, Internet | All internal zones |

---

## Part 2 — UI Walkthrough

**Before you start:** Back up config (Settings → System → Backups → Download → Settings
Only). ZBF migration is a one-way door.

**Navigation** (Network 9.4+):
Settings → Zones → **Create Policy**
(or Settings → Policy Table → Create New Policy)

For **each policy**, fill in every field per
[firewall-policy-checklist.md](firewall-policy-checklist.md) (exact UniFi UI selections).

Policies appear in a list — **drag or reorder so #1 is at the top**. Match
[firewall-policy-order.md](firewall-policy-order.md).

---

## Phase A — Confirm Gateway access (do this first)

- [ ] Check if UniFi already created built-in Gateway policies
- [ ] Create any missing policies from the table below
- [ ] Sanity check: connect a device to IoT VLAN — it gets an IP and resolves DNS

| # | Description | Source | Destination | Ports | Action |
|---|---|---|---|---|---|
| 5 | Trusted → Gateway (DNS/DHCP/NTP) | Trusted | Gateway | UDP 53, 67, 123; TCP 53 | Allow |
| 6 | IoT → Gateway (DNS/DHCP/NTP) | IoT | Gateway | UDP 53, 67, 123 | Allow |
| 7 | Cameras → Gateway (DHCP/NTP only) | Cameras | Gateway | UDP 67, 123 | Allow |
| 8 | Work → Gateway (DNS/DHCP) | Work | Gateway | UDP 53, 67; TCP 53 | Allow |
| 9 | Guest → Gateway (DNS/DHCP) | Hotspot | Gateway | UDP 53, 67; TCP 53 | Allow |

---

## Phase B — Specific allows (above the blocks)

- [ ] Create policies 1a–1h (Internal → every destination zone — see checklist)
- [ ] Create policies 10–13 (internet allows)
- [ ] Confirm Auto Allow Return Traffic is ON on every Allow rule

| # | Description | Source | Destination | Ports | Action |
|---|---|---|---|---|---|
| 1 | Mgmt full access | Internal | *each zone* (8 policies) | Any | Allow |
| 2 | Trusted → IoT control | Trusted | IoT | Any *(tighten later)* | Allow |
| 3 | Trusted → Cameras (view/NVR) | Trusted | Cameras | TCP 80, 443, 554 | Allow |
| 4 | mDNS reflect Trusted↔IoT | Trusted | IoT | AirPlay/Cast/HomeKit ports | Allow |
| 10 | Trusted → Internet | Trusted | External | Any | Allow |
| 11 | IoT → Internet | IoT | External | Any | Allow |
| 12 | Work → Internet | Work | External | Any | Allow |
| 13 | Guest → Internet | Hotspot | External | Any | Allow |

**Note on #4:** mDNS proxy handles *discovery* only. Rule #4 allows *control* traffic
after discovery. See [mdns-multicast-checklist.md](mdns-multicast-checklist.md). Skip #4
until casting works without it; add if cross-VLAN casting fails.

**Note on #2 vs #4:** Rule #2 is the blanket Trusted→IoT allow. Rule #4 is optional
extra scoping for multicast-related ports. Start with #2 as `Any`; tighten both once
things work.

---

## Phase C — Isolation blocks (below the allows)

- [ ] Create policy 14 (Cameras → Internet block)
- [ ] Create policy 14b (IoT → Gateway admin block) — must sit below #6
- [ ] Create policies 15–19 (lateral movement blocks)

| # | Description | Source | Destination | Ports | Action |
|---|---|---|---|---|---|
| 14 | Block Cameras → Internet | Cameras | External | Any | Block |
| 14b | Block IoT → Gateway admin | IoT | Gateway | TCP 22, 80, 443 | Block |
| 15 | Block IoT → Trusted | IoT | Trusted | Any | Block |
| 16 | Block IoT → Internal/Cameras/Work | IoT | Internal, Cameras, Work | Any | Block |
| 17 | Block Cameras → all internal | Cameras | Trusted, IoT, Work, Internal | Any | Block |
| 18 | Block Work → all internal | Work | Trusted, IoT, Cameras, Internal | Any | Block |
| 19 | Block Guest → all internal | Hotspot | any internal zone | Any | Block |

**14b placement:** Must sit **below** #6 (IoT→Gateway DNS/DHCP allow) — different ports,
so DNS/DHCP still works but compromised IoT can't hit the router web UI.

**Multi-destination rules (#16–19):** If UniFi only lets you pick one destination zone
per policy, create one policy per destination (same source, same action) and keep them
grouped below the allows.

---

## Phase D — Final reorder and cleanup

- [ ] Policy list top-to-bottom matches the order below
- [ ] Delete redundant policies from ZBF auto-migration
- [ ] Run [zbf-isolation-verify.sh](../../scripts/network/zbf-isolation-verify.sh) from each VLAN

Your policy list top-to-bottom should read:

1. Mgmt allow — Internal → Internal, Trusted, IoT, Cameras, Work, Hotspot, Gateway, External (8 policies)
2. Trusted → IoT allow
3. Trusted → Cameras allow
4. mDNS Trusted → IoT allow *(optional)*
5–9. Each zone → Gateway allow
10–13. Each zone → External allow (except Cameras)
14. Cameras → External **Block**
14b. IoT → Gateway admin **Block**
15–19. Isolation blocks

---

## Part 3 — Verify ("Done when")

| Test | From | Command / action | Expected |
|---|---|---|---|
| Trusted controls IoT | Phone on Trusted | Open Hue/Nest app, cast to TV | Works |
| IoT isolated from Trusted | Device on IoT | `ping 192.168.10.1` (or any Trusted IP) | **Fails / timeout** |
| Cameras no internet | Camera or laptop on Cameras VLAN | `ping 8.8.8.8` | **Fails** |
| Cameras still get IP | Camera | Check DHCP lease | Has IP |
| Work internet-only | Work laptop | Browse web → works; ping Trusted → fails | Internet yes, LAN no |
| Guest internet-only | Guest device | Same as Work | Internet yes, LAN no |
| Return traffic | Phone on Trusted | Control Hue while IoT→Trusted is blocked | Still works |

Automated checks (from a shell on each VLAN):

```bash
# Auto-detect zone from local IP (192.168.{vlan}.x scheme):
./scripts/network/zbf-isolation-verify.sh

# Or set explicitly:
ZONE=iot TRUSTED_IP=192.168.10.50 ./scripts/network/zbf-isolation-verify.sh
ZONE=cameras ./scripts/network/zbf-isolation-verify.sh
ZONE=work TRUSTED_IP=192.168.10.1 ./scripts/network/zbf-isolation-verify.sh
```

---

## Common mistakes

1. **Blocking Gateway before confirming DHCP/DNS allows** — entire VLAN goes dark
2. **Putting broad blocks above specific allows** — breaks legitimate flows
3. **Turning off Auto Allow Return Traffic** — breaks Trusted→IoT even though you allowed it
4. **Expecting IoT→Trusted Allow for casting** — direction is Trusted→IoT; return is automatic
5. **Enabling mDNS proxy on one VLAN only** — casting discovery fails (see net-06)
6. **Forgetting rule 14b** — IoT can still reach router admin UI on port 443

---

## Authoritative docs

- Policy table: [firewall-policy-order.md](firewall-policy-order.md)
- Zone/VLAN mapping: [vlan-zone-firewall-plan.md](vlan-zone-firewall-plan.md)
- mDNS + rule #4: [mdns-multicast-checklist.md](mdns-multicast-checklist.md)
- [Zone-Based Firewalls in UniFi](https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi)
