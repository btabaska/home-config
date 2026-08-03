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
| rig (CachyOS) | 192.168.10.12 | `cachyos.*.ts.net` | 24/7 — if unreachable, recover via WoL ([runbook](runbooks/wake-the-rig.md)) |
| Home Assistant | 192.168.10.50 | not on tailnet yet (ha track — Run 5 in progress) | :8123 |
| seedbox (Betty) | off-site (shared IP 185.162.184.38) | `seedbox` via Tailscale SSH | No LAN presence |

## VLANs and firewall zones

UniFi Zone-Based Firewall with custom zones. Model: **allow Trusted →
Untrusted; block Untrusted → Trusted; narrow pinholes only.**

| Network (VLAN) | Zone | What's on it |
|---|---|---|
| Default (mgmt) | Internal | UniFi gear only — no clients |
| Trusted | Trusted | PCs, NAS, mini, phones, consoles, HA, Apollo host + Moonlight clients |
| IoT | IoT (untrusted) | Hue bridge, Nest, Midea, smart TVs |
| Cameras (optional) | Cameras | IP cameras — no internet |
| Work | Work | Work laptop — internet only |
| Guest | Hotspot | Visitors, client isolation on |

Details, pinholes, and the one-way-door migration warning:
`reference/network/vlan-zone-firewall.md` and the firewall-policy docs in
`configs/network/`. mDNS/IoT auto-discovery is enabled between Trusted and IoT
(IGMP snooping OFF) so casting, HA discovery, and Moonlight keep working —
this is why gaming/streaming stays on Trusted, not its own VLAN.

### Docker bridges must not squat on the LAN/VLAN space

The VLANs live in `192.168.10-50.0/24`. Docker on the mini hands compose stacks
their own bridge subnets, and its **legacy** default pool used
`192.168.0.0/16` in `/20` blocks — so a bridge could silently claim a range
that *contains* a VLAN `/24` and blackhole it host-wide. This bit us in
fix-66 (fleet-sweep SH6): the `journaling` stack's bridge grabbed
`192.168.16.0/20` (spans `.16.0-.31.255`), which swallowed the **IoT** VLAN
`192.168.20.0/24` — `ip route get 192.168.20.100` resolved into the local
bridge, so the mini could no longer reach the Hue bridge or any IoT device
(HA, on a different host, was unaffected, so lights still worked). Two guards:

- **Daemon pool** — `/etc/docker/daemon.json` `default-address-pools` is pinned
  to `172.16.0.0/12` + `10.201.0.0/16` (fix-19), off the LAN space, so *new*
  auto-assigned bridges land safely.
- **Pin the subnet on any bridge that must be stable**, off `192.168.x`. The
  journaling bridge is now pinned to `10.201.16.0/24` in its compose. Changing a
  bridge subnet needs a **network recreate** (`compose down` + `up`), not `up -d`.

Two checks cover this: `net-trusted-to-iot-reachable` (net-05 — probes the Hue
bridge from the mini) and `sys-docker-vlan-overlap` (fix-66 — subnet arithmetic
that CRITs if any docker bridge overlaps the routable Trusted/IoT VLANs). The
broader `sys-docker-subnet-squat` (ha-19) still warns on the two remaining
`192.168.x` squatters (`scrutiny-collector`, `terraria`) pending their re-home.

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

Status (2026-07-09): the chain is **deployed and continuously guarded** —
dns-02 (NAS secondary up) and dns-03 (DHCP handout) are closed, both
resolvers are probed by the verification sweep's dns checks and Kuma, and a
regression auto-reopens the task. Still open: the scripted outage *drill*
(dns-04, optional) and gateway NAT-redirect/DoH-blocking hardening (dns-05,
gated on it). If names stop resolving, go straight to the
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
  real TLS and nothing exposed publicly except the one documented port below.

## Edge / WAN exposure

Ground truth (established 2026-07-17, quality-gate fix-24 — M61/L53):

- **Exactly one inbound WAN port is open: `32400` → NAS Plex.** Plex Remote
  Access is **intentional** (operator decision 2026-07-17) so household users
  can stream without Tailscale. It is a **manual port-forward on the
  operator-managed Dream Wall**, not UPnP: the gateway offers **no UPnP IGD and
  no NAT-PMP** (verified with `upnpc`/`natpmpc` from the mini), so no LAN
  device can silently open additional ports. The unauthenticated Plex
  `/identity` endpoint is reachable from the internet by design (version +
  machine id disclosure); everything token-gated stays token-gated.
- **Public DNS for `tabaska.us` contains no host records.** The zone is Proton
  mail records, playit.gg NS delegations (`minecraft`/`palworld`/`bedrock`),
  and TXT only; every service name is NXDOMAIN publicly and resolves only via
  the AdGuard split-horizon rewrites. The old `www → 192.168.10.2` public A
  record (RFC1918 leak, finding L53) was deleted from the Cloudflare zone
  2026-07-17.
- **Continuously guarded** by `verification/checks.d/edge.yaml`: a WAN port
  sweep from the seedbox (true off-net vantage — LAN-side probes only test NAT
  hairpin) that pages `crit` on any port besides 32400; a pinned
  machineIdentifier probe of the exposed Plex; a CVE-posture check that warns
  if the exposed Plex build lags the latest Synology release by >14 days; and a
  Cloudflare zone audit that fails on any private-IP record. Runbook:
  [edge exposure](runbooks/edge-exposure.md).

## Tailscale

Every host you own runs Tailscale; it is the remote-access layer and the
primary SSH path (`tailscale up --ssh`, ACL-gated — see
`configs/network/tailscale-acl-ssh.hujson`). Break-glass fallback: a classic
ed25519 key + `~/.ssh/config` aliases (`ssh mini`, `ssh nas`, `ssh rig`,
`ssh seedbox`), tracked by chezmoi. For streaming/gaming over Tailscale,
verify the connection is **direct**, not DERP-relayed (`tailscale status`);
forward UDP 41641 on the gateway if not.

The early tailnet-ACL gap that blocked operator → seedbox SSH is **fixed**
— `ssh seedbox` works (verified 2026-07-09).
