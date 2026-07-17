# Edge / WAN exposure

What to do when an `edge-*` verification check fires (ntfy topic
`verification`). Context: [Network → Edge / WAN exposure](../network.md#edge-wan-exposure).
The intended posture is **one open WAN port (32400 → NAS Plex, intentional)**
and **zero host records in public DNS**.

## `edge-wan-port-posture` failed (crit) — an unexpected WAN port is open

The seedbox-side sweep found a port besides 32400 answering on the home WAN IP.
The check output lists it (`UNEXPECTED_OPEN:<ports>`).

1. Confirm from a second off-net vantage (phone hotspot):
   `nc -vz -w 5 $(ssh mini 'curl -s ifconfig.me') <port>`.
2. Identify what answered: `curl -sv http://<wan-ip>:<port>/` — service banners
   usually identify the culprit; cross-check which LAN host runs that service.
3. The gateway offers **no UPnP/NAT-PMP** (verified 2026-07-17), so a new open
   port means someone/something added a **manual forward on the Dream Wall**
   (GUI-only, operator-managed) — or that verification itself is broken.
   Review Dream Wall → Settings → Firewall/NAT → Port Forwarding and delete
   anything undocumented; if it was added deliberately, document it in
   [network.md](../network.md#edge-wan-exposure) and extend the check's
   allowlist instead.
4. `NO_WAN_IP` output means the mini couldn't learn its WAN IP
   (`https://ifconfig.me` unreachable) — a vantage failure, not an exposure.

## `edge-plex-remote-identity` failed (warn) — :32400 no longer serves our Plex

- **Nothing answers**: Plex Remote Access broke (a feature the operator wants).
  Check the NAS Plex package is running, then Plex → Settings → Remote Access.
  If the WAN IP changed, the Dream Wall forward still points at the NAS, so
  this usually self-heals; persistent failure → re-check the forward rule.
- **Something answers but the machineIdentifier differs**: treat as an
  incident — a different service/host is behind the forward. Close the forward
  first, investigate second.

## `edge-plex-version-current` failed (warn) — exposed Plex build is stale

The internet-facing Plex has been more than 14 days behind the latest Synology
DSM 7.2.2+ release — unpatched-CVE exposure on the one port we deliberately
leave open. Update via DSM Package Center on the NAS (or download the current
`.spk` from plex.tv/media-server-downloads → Synology DSM 7.2.2+). A brief
stream interruption is expected; prefer the 4–7AM window.

## `edge-public-dns-no-rfc1918` / `edge-public-dns-www-nxdomain` failed (warn)

A record in the public `tabaska.us` Cloudflare zone points at a private IP, or
`www.tabaska.us` publicly resolves again (the exact L53 regression — it leaked
`192.168.10.2` until deleted 2026-07-17).

1. List the zone: Cloudflare dashboard, or with the API token (vault
   `cloudflare.api_token`, also in mini `/etc/verification/env`).
2. Delete the offending record — internal names belong in the AdGuard rewrites
   (split-horizon), never in public DNS. Legitimate public entries are Proton
   mail records, playit NS delegations, and TXT.
3. Verify: `dig @1.1.1.1 <name> A` → NXDOMAIN, then re-run
   `run-checks.sh --host edge --no-notify` on the mini.

## Re-run the checks

```bash
ssh mini 'set -a; . /etc/verification/env; set +a; \
  /opt/verification/bin/run-checks.sh --host edge --no-notify --json'
```
