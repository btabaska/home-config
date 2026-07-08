# Runbook — DNS outage

**Symptom:** devices show "connected" but nothing resolves, or
`*.tabaska.us` names die while the internet still works.

## The resolver chain (what should be true)

```
client DHCP DNS (every VLAN):
  #1  192.168.10.2   mini AdGuard  → local Unbound (recursive, DNSSEC)
  #2  192.168.10.4   NAS AdGuard   → public DoT (1.1.1.1 / 9.9.9.9)
  #3  192.168.10.1   UniFi gateway → bare internet DNS
Both AdGuards rewrite  *.tabaska.us → 192.168.10.2
```

Design intent: mini down ⇒ clients fall to the NAS (filtering + local names
survive); mini **and** NAS down ⇒ gateway (internet survives, local names and
filtering are gone until an AdGuard returns).

!!! warning "Known state (2026-07-07 audit)"
    The chain is not yet healthy: the NAS secondary was down and the DHCP
    handout listed off-subnet `192.168.1.1` instead of the NAS/gateway
    (pending: dns-02 restart, dns-03 fix in UniFi, dns-04 drill). Until those
    close, a mini outage kills all local names.

## Test each hop (from any LAN machine)

```bash
# Hop 1 — mini AdGuard: external name + local rewrite
dig @192.168.10.2 example.com +time=2 +tries=1
dig @192.168.10.2 wiki.tabaska.us +short        # expect 192.168.10.2

# Hop 2 — NAS AdGuard: must work with the mini DOWN (independent upstream)
dig @192.168.10.4 example.com +time=2 +tries=1
dig @192.168.10.4 wiki.tabaska.us +short        # expect 192.168.10.2

# Hop 3 — gateway: external only (no local names expected)
dig @192.168.10.1 example.com +time=2 +tries=1

# What is DHCP actually handing out? (macOS)
ipconfig getpacket en0 | grep domain_name_server
# expect: {192.168.10.2, 192.168.10.4, 192.168.10.1}
```

Scripted version of the whole drill: `scripts/network/dns-resilience-verify.sh`
(dns-04).

## Diagnosis → fix

| Finding | Cause | Fix |
|---|---|---|
| Hop 1 dead, hop 2 answers | mini down/rebooting — **expected, self-heals** | Wait it out or fix the mini; clients ride hop 2 |
| Hop 1 dead, hop 2 dead | NAS AdGuard container not running | DSM → Container Manager → project `adguard-nas` → Start. UI: `http://192.168.10.4:3000` |
| Hop 1 up but external names fail | Unbound broken behind AdGuard | `ssh mini 'cd /opt/stacks/unbound && docker compose logs --tail 50'`; restart the unbound stack |
| Local names fail only on hop 2 | Rewrites not mirrored to NAS AdGuard | Re-import rewrites/blocklists from the mini instance (dns-02) |
| DHCP handout wrong | Out-of-band UniFi change | **Human, GUI**: Settings → Networks → each VLAN → DHCP DNS = `10.2, 10.4, 10.1` exactly; then log one line in the state doc |
| Everything dead incl. hop 3 | Gateway down | Bigger problem — see [gateway](../hosts/gateway.md) |

## What fails when the mini is down (so you don't chase ghosts)

All `*.tabaska.us` URLs (Caddy lives there) — **even though DNS still
resolves them** via the NAS rewrite, the proxy behind the IP is down. Direct
ports keep working: Immich `192.168.10.4:2283`, Plex, DSM, HA `:8123`.

## Verify after any fix

```bash
bash foss-setup/scripts/network/dns-resilience-verify.sh
```

All three hops answer + rewrite correct on both AdGuards = green.
