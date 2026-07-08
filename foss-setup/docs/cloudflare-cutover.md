# Cloudflare cutover — tabaska.us (keeping brandon@tabaska.us working)

Written 2026-07-08 from a live enumeration of the zone. Current state: registrar is
**Squarespace**, DNS is served by legacy Google Cloud DNS (`ns-cloud-c{1..4}.googledomains.com`),
and email is **Proton Mail** (that's what keeps brandon@tabaska.us alive).

**Why email survives this**: mail delivery only cares about the MX/TXT *records*, not who
serves them. If Cloudflare has identical records before you flip the nameservers, there is
zero mail downtime — resolvers get the same answers from either side during propagation.

## Records that MUST exist in Cloudflare before the switch

| Type | Name | Value | Proxy |
|------|------|-------|-------|
| MX | `tabaska.us` | `mail.protonmail.ch` priority **10** | DNS-only (forced) |
| MX | `tabaska.us` | `mailsec.protonmail.ch` priority **20** | DNS-only (forced) |
| TXT | `tabaska.us` | `v=spf1 include:_spf.protonmail.ch mx ~all` | — |
| TXT | `tabaska.us` | `protonmail-verification=61e4e54d…` (copy exactly from current zone) | — |
| A | `www` | `192.168.10.2` | **DNS-only (grey cloud)** — it's a private IP; proxying breaks it |

That is the complete public zone today (root