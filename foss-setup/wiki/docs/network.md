# Network

Everything hangs off the **UniFi Dream Wall** (router + firewall + 17-port
switch + WiFi 6 + controller) at `192.168.10.1`. Fiber → ISP ONT (bridge
mode) → Dream Wall → devices.

## Per-host IPs

| Host | LAN IP | Tailscale | Notes |
|---|---|---|---|
| gateway (Dream Wall) | 192.168.10.1 | — | GUI-only management |
| mini | 192.168.10.2 | `macmini.tailb31641.ts.net` | Caddy 80/443, DNS :53, Forgejo :3030 (HTTP) |
| nas (DS920+) | 192.168.10.4 | `nas.*.ts.net` | DSM, Immich :2283, AdGuard secondary :53/:3000 |
| rig (CachyOS) | 192.168.10.12 | `cachyos.*.ts.net` | On-demand — wake first ([runbook](runbooks/wake-the-rig.md)) |
| Home Assistant | 192.168.10.50 | not on tailnet yet (pending: ha-01) | :8123 |
| seedbox (Betty) | off-site (shared IP 185.162.184.38) | `seedbox` via Tailscale SSH | No LAN presence |

## VLANs and firewall zones

UniFi Zone-Based Firewall with custom zones. Model: **allow Trusted →
Untrusted; block Untrusted → Trusted; narrow pinholes only.**

| Network (VLAN) | Zone | What's on it |
|---|---|---|
| Default (mgmt) | Internal | UniFi gear only — no clients |
| Trusted | Trusted | PCs, NAS, mini, phones, consoles, HA, Sunshine host + Moonlight clients |
| IoT | IoT (untrusted) | Hue bridge, Nest, Midea, smart TVs |
| Cameras (optional) | Cameras | IP cameras — no internet |
| Work | Work | Work laptop — internet only |
| Guest | Hotspot | Visitors, client isolation on |

Details, pinholes, and the one-way-door migration warning:
`configs/network/vlan-zone-firewall-plan.md` and the firewall-policy docs in
`configs/network/`. mDNS/IoT auto-discovery is enabled between Trusted and IoT
(IGMP snooping OFF) so casting, HA discovery, and Moonlight keep working —
this is why gaming/streaming stays on Trusted, not its own VLAN.

## DNS — the resolver chain

Target DHCP DNS chain on **every client VLAN** (fail-open, in this order):

```
#1  192.168.10.2   mini AdGuard    — filtering + *.tabaska.us rewrites (primary)
#2  192.168.10.4   NAS AdGuard     — same rewrites, independent DoT upstream (secondary)
#3  192.168.10.1   UniFi gateway   — bare internet DNS, survival fallback
```

On the mini, AdGuard forwards to a local **Unbound** (recursive, DNSSEC — no
upstream sees queries). The NAS secondary deliberately uses public DoT
(`tls://1.1.1.1`, `tls://9.9.9.9`) so it still resolves when the mini is down.
The design rule: **"filtering off" must never mean "internet off"** (incident
2026-07-03 — a mini reboot took DNS down house-wide).

Status: the chain is **not yet correctly deployed** — the NAS secondary was
down and the DHCP handout wrong at the 2026-07-07 audit (pending: dns-02,
dns-03, dns-04). If names stop resolving, go straight to the
[DNS outage runbook](runbooks/dns-outage.md).

## `*.tabaska.us` — the wildcard and Caddy

- Both AdGuard instances carry a DNS rewrite: `*.tabaska.us → 192.168.10.2`.
- **Caddy on the mini owns 80/443** and terminates TLS for every service, with
  a wildcard cert via Cloudflare DNS-01 (custom Caddy build with the
  Cloudflare module — see `configs/docker-stack/stacks/caddy/`).
- Services on the mini are proxied **by container name** over the shared
  external `edge` Docker network (`docker network create edge` — a hard
  prerequisite). NAS / rig / seedbox services are proxied **by IP** via the
  `NAS_IP` / `RIG_IP` / `SEEDBOX_IP` env vars in `caddy/.env`.
- Result: `https://<name>.tabaska.us` works LAN-wide (and over Tailscale) with
  real TLS and nothing exposed publicly.

## Tailscale

Every host you own runs Tailscale; it is the remote-access layer and the
primary SSH path (`tailscale up --ssh`, ACL-gated — see
`configs/network/tailscale-acl-ssh.hujson`). Break-glass fallback: a classic
ed25519 key + `~/.ssh/config` aliases (`ssh mini`, `ssh nas`, `ssh rig`,
`ssh seedbox`), tracked by chezmoi. For streaming/gaming over Tailscale,
verify the connection is **direct**, not DERP-relayed (`tailscale status`);
forward UDP 41641 on the gateway if not.

Known gap: the tailnet ACL currently **blocks operator → seedbox SSH**
(pending: human queue — add an SSH rule in the Tailscale admin console).
