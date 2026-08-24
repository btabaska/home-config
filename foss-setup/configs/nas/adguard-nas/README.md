# AdGuard Home — NAS secondary DNS

DHCP DNS **#2** (`192.168.10.4`). See [dns-resilience-plan.md](../../../network/dns-resilience-plan.md).

**Do not** point upstream at mini Unbound — the secondary must work when the mini is offline.

After deploy, mirror DNS rewrites from mini (`*.tabaska.us → 192.168.10.2`) and optionally
import the same blocklists.

## Upstream DNS resolvers (fix-89, 2026-08-23)

The resolver config lives in the live-only `conf/AdGuardHome.yaml` (not mirrored —
managed via the AdGuard UI/API). Intended `upstream_dns` (rebuild must restore
FAILOVER, not a single upstream):

```yaml
upstream_dns:
  - https://dns10.quad9.net/dns-query   # Quad9 DoH (no-malware, no-eDNS variant)
  - https://cloudflare-dns.com/dns-query
  - https://dns.quad9.net/dns-query     # Quad9 DoH (standard)
```

Why: the 2026-08-23 sweep (UM55/UL138) found the secondary resolver had a SINGLE
upstream (`dns10.quad9.net` DoH) that flooded `unexpected EOF` (98% of logs),
intermittently failing external resolution. Multiple upstreams let AdGuard fail
over when one DoH endpoint resets. Verified: `dig @192.168.10.4 cloudflare.com`
resolves; the `dns-secondary-resolves-example-com` check (dns.yaml) is now reliable.
