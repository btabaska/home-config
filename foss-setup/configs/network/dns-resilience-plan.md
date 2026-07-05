# DNS resilience plan — fail-open, not fail-closed

> **Incident (2026-07-03):** UniFi DHCP pointed all VLANs at a single AdGuard instance on
> the Mac mini (`192.168.10.2`). When the mini rebooted, every device using that DNS server
> lost name resolution — Apple TVs, phones, and other WiFi clients showed “connected” but
> had no working internet. The MacBook partially worked because its lease had gateway DNS
> (`192.168.10.1`) plus Tailscale supplemental DNS.

**Root cause:** architecture, not AdGuard software. Any resolver (AdGuard, Pi-hole, Unbound)
becomes a house-wide outage if it is the **only** DHCP DNS with no fallback.

This doc is the authoritative fix. Implement via rollout tasks **dns-02** through **dns-05**
before pointing client DHCP at AdGuard again.

---

## Target architecture

```
Client DHCP DNS chain (every VLAN):
  #1  192.168.10.2   Mac mini AdGuard  — filtering + *.tabaska.us rewrites (primary)
  #2  192.168.10.4   NAS AdGuard       — same rewrites, independent upstream (secondary)
  #3  192.168.10.1   UniFi gateway     — bare internet DNS, no filtering (survival fallback)
```

### Failure modes

| What dies | Client behavior |
|-----------|-----------------|
| Mini reboot (~30–60 s) | Clients retry → NAS AdGuard → internet keeps working |
| Mini + NAS both down | Clients retry → gateway DNS → **public internet works**; lose filtering + `*.tabaska.us` until AdGuard returns |
| Gateway down | Bigger problem — nothing fixes that |

**Design rule:** never deploy DNS in a way that makes “filtering off” synonymous with “internet off.”

---

## Task map

| Task | What | AI can run? |
|------|------|-------------|
| **dns-01** | Core on mini (Unbound + AdGuard + rewrites) — **done** | Partial (core was auto) |
| **dns-02** | Secondary AdGuard on NAS + mirror rewrites/blocklists | **Yes** — compose + config sync |
| **dns-03** | UniFi DHCP fail-open chain on all client VLANs | **No** — UniFi GUI (you click) |
| **dns-04** | Verify script + outage runbook | **Yes** — script in repo |
| **dns-05** | NAT `:53` redirect + DoH blocking | **No** — UniFi GUI; **only after dns-03** |

Do **not** enable NAT `:53` redirect (dns-05) until dns-03 is live. Redirect removes the
gateway fallback path and recreates the single-point-of-failure.

---

## dns-02 — NAS secondary AdGuard

- Deploy `configs/docker-stack/stacks/adguard-nas/` on the NAS (Container Manager).
- **Upstream:** public DoT (e.g. `tls://1.1.1.1`, `tls://9.9.9.9`) — **not** mini Unbound.
  The secondary must resolve names when the mini is offline.
- **DNS rewrites:** mirror every `*.tabaska.us → 192.168.10.2` rule from mini AdGuard.
- Export mini AdGuard config periodically (Settings → Export) or automate via API;
  import blocklists/rewrites to NAS instance.

NAS LAN IP for DHCP secondary: **`192.168.10.4`** (eth1; same subnet as mini).

---

## dns-03 — UniFi DHCP (manual)

For **Trusted, IoT, Guest, and Work** networks (any VLAN that serves clients):

1. Settings → Networks → [network] → DHCP → DNS Server
2. Set **three** servers in order: `192.168.10.2`, `192.168.10.4`, `192.168.10.1`
3. Save; optionally shorten lease time to 1 h once to speed client migration, then restore 24 h

Until dns-03 is done, keep gateway (`192.168.10.1`) as primary or sole DNS if the mini is
unreliable — filtering is optional; internet is not.

---

## dns-04 — Verify

From the MacBook (Trusted VLAN):

```bash
./scripts/network/dns-resilience-verify.sh
```

Simulate mini outage: stop AdGuard on mini, confirm `dig @192.168.10.4 google.com` and
`dig @192.168.10.1 google.com` still work.

---

## dns-05 — Anti-bypass (deferred, optional hardening)

Only after dns-03 verified:

- Dream Wall: NAT-redirect outbound UDP/TCP `:53` → `192.168.10.2` (with NAS as alternate target in policy if supported)
- Block known DoH provider endpoints (force filtered path)

Accept the tradeoff: redirect + no gateway fallback = harder bypass, but mini outage becomes
more painful unless NAS secondary is proven solid.

---

## Outage runbook (quick reference)

1. **Symptom:** WiFi connected, no internet/apps on some devices
2. **Check:** `ping 192.168.10.2` and `dig @192.168.10.2 google.com +time=2`
3. **Immediate fix:** UniFi → set DHCP DNS to `192.168.10.1` (gateway) on affected VLANs
4. **On stuck clients:** Renew DHCP lease or toggle Wi‑Fi
5. **Restore:** power-cycle mini; confirm AdGuard `:53` responds; revert DHCP to fail-open chain

---

## Related docs

- [dns-01 task](../scripts/docs/task-overrides.json) — core resolver
- [adguard compose](../docker-stack/stacks/adguard/compose.yaml) — mini primary
- [adguard-nas compose](../docker-stack/stacks/adguard-nas/compose.yaml) — NAS secondary
- [vlan-zone-firewall-plan.md](vlan-zone-firewall-plan.md) — IoT → Gateway DNS allow (#6)
