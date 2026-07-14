# DNS resilience (fail-open)

> How home DNS is architected so a single resolver reboot never becomes a house-wide internet outage.

_Source: `foss-setup/configs/network/dns-resilience-plan.md` · migrated + validated 2026-07-14._

!!! note "Incident (2026-07-03)"
    UniFi DHCP pointed all VLANs at a single AdGuard instance on the Mac mini
    (`192.168.10.2`). When the mini rebooted, every device using that DNS server lost
    name resolution — Apple TVs, phones, and other WiFi clients showed "connected" but
    had no working internet. The MacBook partially worked because its lease had gateway
    DNS (`192.168.10.1`) plus Tailscale supplemental DNS.

**Root cause:** architecture, not AdGuard software. Any resolver (AdGuard, Pi-hole, Unbound)
becomes a house-wide outage if it is the **only** DHCP DNS with no fallback.

**Design rule:** never deploy DNS in a way that makes "filtering off" synonymous with "internet off."

## Target architecture

The client DHCP DNS chain on **every VLAN** is three servers, in order:

| # | Server | Role |
|---|--------|------|
| 1 | `192.168.10.2` | Mac mini AdGuard — filtering + `*.tabaska.us` rewrites (primary) |
| 2 | `192.168.10.4` | NAS AdGuard — same rewrites, independent public-DoT upstream (secondary) |
| 3 | `192.168.10.1` | UniFi gateway — bare internet DNS, no filtering (survival fallback) |

### Failure modes

| What dies | Client behavior |
|-----------|-----------------|
| Mini reboot (~30–60 s) | Clients retry → NAS AdGuard → internet keeps working |
| Mini + NAS both down | Clients retry → gateway DNS → **public internet works**; lose filtering + `*.tabaska.us` until AdGuard returns |
| Gateway down | Bigger problem — nothing fixes that |

## Current state (validated 2026-07-14)

All three resolvers answer on `:53`, and the fail-open architecture below is in place:

- **Primary — mini AdGuard** (`192.168.10.2`): live; resolves `*.tabaska.us → 192.168.10.2`.
- **Secondary — NAS AdGuard** (`192.168.10.4`): **live** — `adguard/adguardhome:v0.107.77`,
  protection enabled, DNS on `:53`, break-glass admin at
  <http://192.168.10.4:3000>. Mirrors the `*.tabaska.us → 192.168.10.2` rewrites and uses a
  public DoT upstream (**not** mini Unbound), so it resolves when the mini is offline.
- **Fallback — gateway** (`192.168.10.1`): live; bare internet DNS, no `*.tabaska.us` rewrites (by design).

This means the original **dns-02** rollout (deploy the NAS secondary + mirror rewrites) is
**done**. The remaining open work is the UniFi-GUI steps (dns-03 / dns-05) below.

## Task map

| Task | What | AI can run? | Status |
|------|------|-------------|--------|
| **dns-01** | Core on mini (Unbound + AdGuard + rewrites) | Partial (core was auto) | done |
| **dns-02** | Secondary AdGuard on NAS + mirror rewrites/blocklists | Yes — compose + config sync | **done** (validated 2026-07-14) |
| **dns-03** | UniFi DHCP fail-open chain on all client VLANs | No — UniFi GUI (you click) | open |
| **dns-04** | Verify script + outage runbook | Yes — script in repo | done |
| **dns-05** | NAT `:53` redirect + DoH blocking | No — UniFi GUI; **only after dns-03** | deferred |

!!! warning
    Do **not** enable the NAT `:53` redirect (dns-05) until dns-03 is live. Redirect removes
    the gateway fallback path and recreates the single-point-of-failure.

## dns-02 — NAS secondary AdGuard (deployed)

- Deployed from `configs/docker-stack/stacks/adguard-nas/` on the NAS (Container Manager),
  image pinned to `adguard/adguardhome:v0.107.77`, container `adguardhome-nas`, LAN IP
  `192.168.10.4` (eth1; same subnet as mini).
- **Upstream:** public DoT (e.g. `tls://1.1.1.1`, `tls://9.9.9.9`) — **not** mini Unbound.
  The secondary must resolve names when the mini is offline.
- **DNS rewrites:** mirror every `*.tabaska.us → 192.168.10.2` rule from mini AdGuard
  (confirmed live: `192.168.10.4` returns `192.168.10.2` for `vault.tabaska.us`).
- Keep it in sync: export mini AdGuard config periodically (Settings → Export) or automate
  via API; import blocklists/rewrites to the NAS instance.

## dns-03 — UniFi DHCP (manual, open)

For **Trusted, IoT, Guest, and Work** networks (any VLAN that serves clients):

1. Settings → Networks → [network] → DHCP → DNS Server
2. Set **three** servers in order: `192.168.10.2`, `192.168.10.4`, `192.168.10.1`
3. Save; optionally shorten lease time to 1 h once to speed client migration, then restore 24 h

Until dns-03 is done, keep gateway (`192.168.10.1`) as primary or sole DNS if the mini is
unreliable — filtering is optional; internet is not.

## dns-04 — Verify

From the MacBook (Trusted VLAN):

```bash
./scripts/network/dns-resilience-verify.sh
```

The script checks all three resolvers resolve `google.com`, and that mini + NAS also resolve
the internal rewrite (`home.tabaska.us`); it exits non-zero on any failure. To simulate a
mini outage, stop AdGuard on the mini and confirm `dig @192.168.10.4 google.com` and
`dig @192.168.10.1 google.com` still work.

## dns-05 — Anti-bypass (deferred, optional hardening)

Only after dns-03 is verified:

- Dream Wall: NAT-redirect outbound UDP/TCP `:53` → `192.168.10.2` (with NAS as alternate
  target in policy if supported)
- Block known DoH provider endpoints (force the filtered path)

Accept the tradeoff: redirect + no gateway fallback = harder bypass, but a mini outage becomes
more painful unless the NAS secondary is proven solid.

## Outage runbook (quick reference)

1. **Symptom:** WiFi connected, no internet/apps on some devices
2. **Check:** `ping 192.168.10.2` and `dig @192.168.10.2 google.com +time=2`
3. **Immediate fix:** UniFi → set DHCP DNS to `192.168.10.1` (gateway) on affected VLANs
4. **On stuck clients:** renew DHCP lease or toggle Wi-Fi
5. **Restore:** power-cycle mini; confirm AdGuard `:53` responds; revert DHCP to the fail-open chain

---
[← Network reference](index.md)
