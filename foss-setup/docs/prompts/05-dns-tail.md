# Handoff 05 — DNS-chain hardening tail (#16) · depends on 04 · NEEDS-USER

Prereqs: item 04 (network re-audit) must be done — you need the real per-VLAN DHCP DNS state first. Read `configs/network/dns-resilience-plan.md`. Loop applies, but note several steps are **manual UniFi UI actions the user must perform** — do the diagnosable/scriptable parts, then hand the user an exact click-list for the rest.

The fail-open 3-tier DNS chain (mini AdGuard `.2` → NAS AdGuard `.4` → gateway `.1`) is deployed; this is the remaining tail:
- **dns-03** — ensure every client VLAN's DHCP hands out `[192.168.10.2, 192.168.10.4, 192.168.10.1]` in that order. From item 04 you know which VLANs already do. For any that don't, produce the exact UniFi path for the user (Settings → Networks → <vlan> → DHCP Name Server → Manual → the three IPs). Verify after they apply (DHCP lease / `dig` from a client on that VLAN).
- **dns-04** — run the outage drill: `scripts/network/dns-resilience-verify.sh` (simulate mini AdGuard down, confirm resolution fails over to `.4` then `.1`). It's never been run. Execute, capture results, fix anything it surfaces.
- **dns-05** (optional hardening, only after dns-03 verified) — NAT-redirect outbound `:53` to the resolver + block known DoH endpoints. Mostly UniFi UI; prepare the exact config + hand to user.

Harden: a check that both AdGuard resolvers answer + the chain fails over (some may already exist in `checks.d/dns.yaml` — extend, don't duplicate). Negative-test.

Done-criteria: dns-03 verified applied on all client VLANs, dns-04 drill run+passing, dns-05 prepared (applied if user does the UI step). Commit; check item 05 off; update the task board. If blocked on user UI actions, leave partial progress noted in the queue item and report the exact click-list.
