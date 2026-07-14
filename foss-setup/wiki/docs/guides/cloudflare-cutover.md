# Cloudflare cutover

> Moving DNS for `tabaska.us` to Cloudflare while keeping `brandon@tabaska.us` (Proton Mail) delivering with zero downtime.

_Source: `foss-setup/docs/cloudflare-cutover.md` · migrated + validated 2026-07-14._

> **STATUS — DONE (validated 2026-07-14).** This started as a cutover plan written 2026-07-08 against the pre-migration zone (registrar Squarespace, DNS still on legacy Google Cloud DNS). **The cutover has since happened.** Live `dig` confirms `tabaska.us` is now served by Cloudflare (`courtney.ns.cloudflare.com` / `ryan.ns.cloudflare.com`, zone active) and every "must exist" record below is present and correct. The registrar is **still Squarespace** — only the nameservers moved. This page is kept as the record of what was migrated and *why mail survived*, and as the reference if the zone ever has to be rebuilt. The full-audit doc corroborates the delegation (`docs/research/12-full-audit-2026-07.md`).

## Starting state (2026-07-08, pre-cutover)

- **Registrar:** Squarespace (unchanged by this move; whois still shows `Squarespace Domains II LLC`).
- **DNS (before):** legacy Google Cloud DNS — `ns-cloud-c{1..4}.googledomains.com`.
- **DNS (now, live):** Cloudflare — `courtney.ns.cloudflare.com`, `ryan.ns.cloudflare.com`.
- **Email:** Proton Mail — this is what keeps `brandon@tabaska.us` alive.

**Why email survives this cutover:** mail delivery only cares about the MX/TXT *records*, not who serves them. If Cloudflare holds identical records before the nameservers are flipped, there is zero mail downtime — resolvers get the same answers from either side during propagation.

## Records that MUST exist in Cloudflare before the switch

These were staged in Cloudflare *before* the nameserver flip, and are all live today.

| Type | Name | Value | Proxy |
|------|------|-------|-------|
| MX | `tabaska.us` | `mail.protonmail.ch` priority **10** | DNS-only (forced) |
| MX | `tabaska.us` | `mailsec.protonmail.ch` priority **20** | DNS-only (forced) |
| TXT | `tabaska.us` | `v=spf1 include:_spf.protonmail.ch mx ~all` | — |
| TXT | `tabaska.us` | `protonmail-verification=61e4e54dc849d8ea1f9ec916e184e344643d1175` (copy exactly from the current zone) | — |
| A | `www` | `192.168.10.2` | **DNS-only (grey cloud)** — it's a private IP; proxying it would break it |

That was the complete public zone at cutover time (root `A`/`AAAA`/`CNAME`, `_dmarc`, and Proton DKIM CNAMEs were **not** present in the zone — do not invent them). MX records are DNS-only by force (Cloudflare cannot proxy mail). The `www` A record points at the mini's private LAN address and must stay grey-cloud (DNS-only) so Cloudflare doesn't try to proxy an unroutable RFC-1918 IP.

_Note: the 2026-07-08 source doc is truncated mid-sentence here; the row above is the complete record set as verified live on 2026-07-14._

## Cutover procedure (as executed)

1. **Stage every record above in Cloudflare** while the zone is still on Google Cloud DNS. Confirm each value matches the current zone exactly — especially the `protonmail-verification` TXT (copy it verbatim; a mismatch here can un-verify the domain in Proton).
2. **Force MX records DNS-only** (grey cloud) — Cloudflare does this automatically for MX, but verify.
3. **Set `www` to DNS-only** (grey cloud) because `192.168.10.2` is a private IP.
4. **Flip the nameservers** at the Squarespace registrar to the Cloudflare pair (`courtney` / `ryan.ns.cloudflare.com`). Registrar ownership stays at Squarespace.
5. **Wait for propagation.** During propagation resolvers get identical MX/SPF answers from both sides, so `brandon@tabaska.us` never loses a beat.

## Verify (live checks)

```bash
dig +short NS  tabaska.us          # -> courtney.ns.cloudflare.com. ryan.ns.cloudflare.com.
dig +short MX  tabaska.us          # -> 10 mail.protonmail.ch.  20 mailsec.protonmail.ch.
dig +short TXT tabaska.us          # -> the SPF line + the protonmail-verification line
dig +short A   www.tabaska.us      # -> 192.168.10.2
whois tabaska.us | grep -i registrar   # -> Squarespace Domains II LLC (registrar unchanged)
```

All five return the expected values as of 2026-07-14.

## Post-cutover notes

- The zone now also carries **game-domain NS delegations** added after the cutover — `minecraft.tabaska.us`, `palworld.tabaska.us`, `bedrock.tabaska.us` are delegated to `ns1`/`ns2.playit-dns.com`. Records under those names are managed in the playit dashboard, not in Cloudflare. That is the playit/game-hosting stack's concern, not this mail-safety cutover.
- **Internal split-horizon is separate from this zone.** `*.tabaska.us` resolving to `192.168.10.2` on the LAN is done by the AdGuard resolvers (mini + NAS rewrites), not by Cloudflare — the public Cloudflare zone does not carry a wildcard.
- **Token scope (least-privilege):** the Caddy DNS-01 token is a *scoped* token, not a global key. Create it from Cloudflare → My Profile → API Tokens → the **Edit zone DNS** template, scoped to **Zone : DNS : Edit** on **`tabaska.us` only** (not all zones). That is the only permission DNS-01 issuance needs — Caddy writes/removes a `_acme-challenge` TXT to prove domain control; the services themselves are never exposed to the internet. It lives in the vault as `cloudflare.api_token` and is injected into Caddy as `CLOUDFLARE_API_TOKEN` (see `services/caddy.md`).
- **Token hygiene (open):** the Cloudflare API token has appeared in chat transcripts and is on the rotation backlog (credential rotations are deferred until the build phase completes — exposure accepted for velocity). If rotated: Cloudflare dashboard → API Tokens → Roll (re-using the same `tabaska.us`-only DNS-edit scope above), then update the vault + Caddy env on the mini, restart Caddy, and verify a cert renewal.

---
[← Guides](index.md)
