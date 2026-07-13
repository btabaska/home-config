# Handoff 04 — Network re-audit vs plan (#15)

Prereqs: read `foss-setup/docs/quality-hardening-state.md` and `foss-setup/configs/network/*.md` (vlan-zone-firewall-plan, firewall-policy-order, dns-resilience-plan, mdns-multicast-checklist, device-onboarding-and-migration). This **corrects an earlier inaccurate finding**: the network is NOT flat — Trusted/IoT/Cameras/Work/Guest VLANs + zone-based firewall + light device migration already exist (all managed hosts read `192.168.10.x` only because that's the Trusted VLAN). This is a **re-audit** (map reality vs plan), not a build. It unblocks #16 (DNS tail) and #4 (HomePod).

Gateway = UniFi Dream Wall at `192.168.10.1`. Check vault for UniFi credentials (there's `unifi_protect`; look for a Network/controller login too). Ways to observe reality, in order of preference:
1. UniFi Network **controller API** (if creds exist) — pull networks/VLANs, subnets, DHCP DNS per network, firewall zones+policies, mDNS proxy scope, IGMP snooping.
2. SSH to the UDW (UniFi OS) if reachable, or read config from there.
3. Infer from the fleet: which subnet each device/host is on, and cross-check the DHCP DNS handed out.
4. **If the UI is the only source of truth for some settings, ask the user for the specific screens** (Settings → Networks, Firewall & Security → Zone Policies, mDNS) — this item is partly user-collaborative.

Produce:
- The **real** VLAN table (id, subnet, DHCP range, DNS servers handed out, mDNS proxy on/off, residents) vs the plan.
- The **real** zone-firewall policy list vs `firewall-policy-order.md` (what's actually enforced; any `any`-scoped rules still to tighten; ZBF migration duplicates left).
- **mDNS/multicast** reality: proxy enabled on which VLANs, IGMP snooping state — specifically whether HomePods (Trusted?) and HA (`.50`, Trusted?) can discover each other, since that gates #4.
- **Device-migration** status: which devices are on their target VLAN vs still on Trusted/default.

Then: correct `configs/network/*.md`, the wiki, and memory to match reality (live state = source of truth); list remaining gaps as precise follow-ups (feed #16 and #4).

Harden (if feasible): a check that the DHCP-handed DNS list and key firewall invariants match the documented intent (e.g. IoT→Trusted blocked, cross-VLAN mDNS reflection present where needed). Negative-test if you add one.

Done-criteria: an accurate network map committed, docs/memory corrected, gaps for #16/#4 enumerated. Commit; check item 04 off; update the task board.
