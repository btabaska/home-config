# 7. "Set it and forget it" configuration

Goal: rebuildable, self-updating-but-not-recklessly, quiet until something needs you.

## Container management (pick one)

- **Dockge** — lightweight, Compose-focused, dead simple, single-host.
- **Dockhand** — the 2025/26 breakout. One container that absorbs logs, resource monitoring, update tracking with *safe pulls* + rollback, notifications (Apprise: ntfy/Telegram/Discord/email), visual Compose editing + Git sync, and Grype/Trivy vulnerability scanning.
- **Komodo** — Rust, Git-driven, multi-server. Best for a fleet; heavier (needs a DB).

**Recommendation:** **Dockhand** for consolidation, or **Dockge** for the simplest. Both beat Portainer now (full SSO/RBAC are Business-Edition; free up to 3 nodes).

## Updates — do this deliberately

**Avoid blind auto-updates.** Watchtower's "always pull latest" model silently breaks a box at 3 am, and the original project was archived (read-only) Dec 2025 (fork `nicholas-fedor/watchtower` continues it). Instead: **pin versions** (`immich:v2.7.5`, not `:latest`); use **notify-only** awareness (Dockhand's tracking, or **Diun** — **live on the NAS**); update on *your* schedule with safe-pull + rollback; read release notes for breaking-change projects (Immich majors especially).

## Monitoring & uptime

- **Beszel** — ultra-light (hub + tiny Go agents), at-a-glance CPU/RAM/disk/network. **Live** (`beszel` + `beszel-agent` on the mini, agents on the NAS/rig).
- **Uptime Kuma** — pings services, alerts on downtime.
- **ntfy** — self-hosted push to your phone. The notification backbone. **Live on the mini.**

## Dashboard & service launcher (one screen for everything)

**Homepage** (the 2026 standard — YAML-configured, tiny footprint, version-controlled next to compose files) — **live on the mini** — covers two needs:

- **For you (observability):** 100+ live **service widgets** pulling status/stats from Plex, Immich, Sonarr/Radarr/Lidarr/Prowlarr/Bazarr, qBittorrent, AdGuard, HA, Uptime Kuma, and **Beszel**, plus container health via Docker labels. Complements (doesn't replace) Beszel/Uptime Kuma.
- **For the household (bookmarks/sharing):** clean tiles — Plex, Immich, Calibre-Web, the request portal (Seerr) — under one memorable URL.
- **Getting it to her devices:** behind **Caddy** (HTTPS), reached over **Tailscale**; a friendly local name like `home.yourdomain`.
- *If per-person boards matter:* **Homarr** (drag-and-drop + user accounts) — heavier, DB-backed, less Git-friendly.

## Remote access

- **Tailscale** — mesh VPN, near-zero config. Install on NAS, Ubuntu box, rig, laptop, and phone; reach services remotely with nothing exposed. Also the path for remote Moonlight and inviting friends to game servers. *(Note: the game servers actually use playit for friends — see Section 4, gaming.)*
- *Full control:* self-host **Headscale** or use **Netbird**. Tailscale's hosted control plane is the pragmatic pick.

## SSH & maintenance access

With ~25 services across 4-5 boxes plus a seedbox, make SSH frictionless and secure once. Lean on Tailscale for the access layer.

- **Tailscale SSH as the primary path.** `tailscale up --ssh` on every node gives **key-less, ACL-gated SSH over the tailnet** — no `authorized_keys` to distribute, no port 22 exposed, works identically in-home and remote. A lost laptop is revoked centrally by de-authing the node.
  - **Lock it down with ACLs + tags.** Tag admin devices `tag:admin` and hosts `tag:server`; an ACL `ssh` rule lets only `tag:admin` SSH `tag:server`. Optional **session recording**.
- **Classic SSH key + `~/.ssh/config` as break-glass.** One **ed25519** keypair in each host's `authorized_keys`, plus aliases over MagicDNS / Tailscale IPs:

```sshconfig
Host nas mini rig ha seedbox
  User admin
  AddKeysToAgent yes
  IdentityFile ~/.ssh/id_ed25519
  ForwardAgent no
Host nas
  HostName nas.tailnet-name.ts.net
Host mini
  HostName mini.tailnet-name.ts.net
Host rig
  HostName rig.tailnet-name.ts.net
```

Maintenance is `ssh nas` / `ssh mini` / `ssh rig`. **Live:** these aliases work (`net-14` done); `ssh mini` has **passwordless sudo**, `ssh nas` needs the vault password. **HA has no SSH** (not a tailnet node) — drive it via REST at `http://192.168.10.50:8123`. Keep `ForwardAgent no` by default. The keypair + config are tracked by **chezmoi** (Section 8, inventory).

- **Per-host quirks:**
  - **Synology DSM** — SSH is off by default; enable it, make it key-based, behind DSM 2FA; don't SSH as `admin`/`root`. DSM resets `sshd_config` on updates, so treat deep SSH customization as non-persistent.
  - **HAOS** — no normal user shell. Use the **SSH & Web Terminal add-on** (key auth) or the `root@<ha-ip>:22222` debug port.
  - **Rig** — runs 24/7, so `ssh rig` just works. Keep the WoL path (`wol`/`etherwake <mac>`) documented as **recovery only**.
  - **Seedbox** — keys-only and hardened; add it to `~/.ssh/config` and the tailnet.
- **Fleet maintenance — one command across every box.** Stand up a tiny **Ansible** setup (agentless — uses the SSH/Tailscale path) with an inventory and small playbooks (patch, ordered reboot, drift audit). Run from the Mac mini or laptop. This is the **manual** lever; it complements the automatic **`unattended-upgrades`** below. Playbooks live in the control repo. Section 9 builds this out fully.

## Reverse proxy + HTTPS

- **Caddy** — automatic HTTPS with a tiny config. The set-and-forget choice. **Live on the mini** (owns 80/443).
- *GUI alternative:* **Nginx Proxy Manager**.
- **Decision — Caddy owns 80/443 on the Mac mini.** It's the single reverse proxy for the whole hand-managed stack: it reaches each service by container name over a shared `edge` Docker network (`reverse_proxy seerr:5055`), so it must be co-located. Container-name routing only covers services on the mini's `edge` network — **NAS and rig services are proxied by IP** via `NAS_IP`/`RIG_IP` env vars in `caddy/.env`. That rules out a second proxy binding 80/443 on the same box.
  - **(A, recommended — and what was chosen) Skip Coolify's proxy; let Caddy front everything.** Ship each vibecoded app as a small Compose stack in `/opt/stacks` (managed by Dockge) + a one-line Caddy vhost (or a `*.app.{$DOMAIN}` wildcard). Same pattern every other service uses — no second proxy, no port fight, no Coolify overhead.
  - **(B) Keep Coolify's git-push workflow, behind Caddy** on alternate ports (8000/8443), Caddy wildcard-proxies `*.app.{$DOMAIN}`. One host, two proxies to reason about.
  - Either way: **don't run two proxies both bound to 80/443 on one host**, and don't split Caddy onto the NAS.

## Self-hosting your own apps (vibecode → live on the LAN)

- **Coolify** — point it at a Git repo, auto-detect the stack via **Nixpacks**, build/deploy/assign a hostname + TLS, redeploy on push. Takes a Dockerfile/Compose too; 280+ templates. *Footprint:* ~600-800 MB + its own Postgres/Redis. Coolify's bundled proxy wants 80/443 (Caddy owns those) so it must run under "behind Caddy on alternate ports."
  - **⚠️ Corrected — Coolify was dropped.** The PaaS half (`docker-14`) is a **non-starter on the 8 GB mini** and was dropped. The chosen and **live** model is **option (A): Caddy-fronted plain Compose stacks** — the static + dynamic + NAS-by-IP + auto-Tailscale Caddy hosting is all live; Coolify is not deployed.
- **LAN visibility:** add a **single wildcard record** in AdGuard — `address=/home.lan/<mac-mini-IP>` — so every `*.home.lan` name resolves to the Mac mini; **Caddy** routes each app by hostname. Shipping a new app is "add a one-line Caddy vhost, pick a name."
- **HTTPS:** plain HTTP on `name.home.lan` is the zero-effort LAN default. For green-padlock local names, give **Caddy** the **DNS-01 challenge** with a real domain (a Cloudflare wildcard cert) without exposing anything.
- **Remote:** reach apps off-LAN over **Tailscale**, no ports opened.
- **Tie-ins:** drop each new app onto **Homepage**; because it lives in Git it inherits the "rebuild in an hour" property.
- *Lighter alternative to Coolify:* **Dokploy** — same git-push model, cleaner UI, lower idle RAM (also not adopted).

## Security hardening (do these once)

- **MFA / 2FA everywhere:**
  - **Crown jewels (hardware key / passkey):** Bitwarden, Proton, the **Synology DSM** admin account, email, and the Tailscale/GitHub/Forgejo accounts. DSM: Control Panel → User → Advanced → enforce 2-step verification (WebAuthn/passkeys).
  - **App-level TOTP:** **Immich**, **Plex**, **Seerr**, **Home Assistant**, the **seedbox** panel, **Forgejo**, **Paperless-ngx** (when deployed), **Vaultwarden** (if used).
  - **Reverse-proxy MFA for the rest:** a forward-auth layer.
- **Exposed-service hardening (only what's reachable).** The Tailscale-first design means the home stack isn't exposed — so this targets the **seedbox** and any **public game-server port-forwards** (now via playit): **CrowdSec** or **fail2ban**, patched, SSH keys-only. For anything published via Caddy, add a forward-auth gate — **Pocket-ID** / **tinyauth** (simple), or **Authelia/Authentik** (full SSO).
- **Docker log rotation (silent disk-fill killer).** Set global caps in `/etc/docker/daemon.json` (`json-file`, `max-size=10m`, `max-file=3`) and restart the daemon.
- **OS security patches.** Enable **`unattended-upgrades`** (Ubuntu) for security-only patches; on CachyOS, update on your own cadence.

> **Note:** credential rotations are **deferred** until the build phase is done (`#18`); exposure is accepted for velocity.

## Config-as-code (makes "rebuild in an hour" true)

Put **all compose files + configs in Git** — self-hosted **Forgejo**, or a private GitHub repo. Disk dies or you migrate → `git clone` + `docker compose up`. Secrets encrypted in-repo with **SOPS + age** (Section 8, inventory).

## Power resilience

- **UPS** on the NAS + Ubuntu box + Dream Wall. DSM reads most consumer UPSes over USB and does a graceful shutdown on battery. The Ubuntu box listens over the network (NUT). **Status: deferred** (`glue-01`) — no budget for a UPS right now.

---
[← index](index.md)
