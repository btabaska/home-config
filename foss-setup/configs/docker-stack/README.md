# Mac mini Docker stack (`/opt/stacks`)

Compose files for the always-on Mac mini (Ubuntu Server, ~12W). Managed with
**Dockge**, which expects each stack in its own folder at `/opt/stacks/<name>/compose.yaml`.
This `stacks/` directory mirrors that layout 1:1 — copy it to `/opt/stacks` on the host
(or keep this repo cloned there) so Dockge discovers every stack.

```
stacks/
  seerr/         # Phase 2 — media request portal (Overseerr/Jellyseerr successor)
  miniflux/      # Phase 3 — RSS reader + PostgreSQL
  navidrome/     # Phase 3 — music streaming
  caddy/         # Phase 4 — reverse proxy + automatic HTTPS
  adguard/       # Phase 4 — network DNS filtering (PRIMARY)
  dockge/        # Phase 4 — container management (SIMPLE DEFAULT)
  beszel/        # Phase 4 — monitoring hub + agent
  uptime-kuma/   # Phase 4 — uptime monitoring / status page
  ntfy/          # Phase 4 — push notifications (the notification backbone)
  diun/          # Phase 4 — image-update notifications (notify-only)
alternatives/
  pihole/        # swap-in for AdGuard Home
  dockhand/      # swap-in for Dockge (power option)
```

## Pinned versions (2026)

Everything is pinned — **never `:latest`**. Updates are *notify-only* via Diun;
you bump tags deliberately after reading release notes.

| Service      | Image (pinned)                      |
|--------------|-------------------------------------|
| Seerr        | `ghcr.io/seerr-team/seerr:v3.2.0`   |
| Miniflux     | `miniflux/miniflux:2.3.0`           |
| PostgreSQL   | `postgres:17-alpine`                |
| Navidrome    | `deluan/navidrome:0.61.2`           |
| Caddy        | `caddy:2.11.4-alpine`               |
| AdGuard Home | `adguard/adguardhome:v0.107.77`     |
| Dockge       | `louislam/dockge:1.5.0`             |
| Beszel       | `henrygd/beszel:0.18.7` (+agent)    |
| Uptime Kuma  | `louislam/uptime-kuma:2.1.1`        |
| ntfy         | `binwiederhier/ntfy:v2.19.2`        |
| Diun         | `crazymax/diun:4.33.0`              |
| _alt:_ Pi-hole  | `pihole/pihole:2026.06.0`        |
| _alt:_ Dockhand | `fnsys/dockhand:v1.0.35`         |

## Recommendations

- **DNS filtering → AdGuard Home (primary).** Single container, built-in
  DoT/DoH/DoQ, per-client rules, cleaner first-run wizard. **Pi-hole** is the
  equally-valid alternative (`alternatives/pihole/`) if you prefer its ecosystem
  or already know it — don't run both as the LAN resolver at once.
- **Container management → Dockge (simple default).** Compose-native, dead
  simple, single-host — perfect for this one box. **Dockhand**
  (`alternatives/dockhand/`) is the power option: logs, metrics history, vuln
  scanning (Grype/Trivy), safe pulls + rollback, Git sync, and Apprise
  notifications in one container. Swap it in if you want to consolidate
  Beszel/Diun-style features into the manager itself.
- **Updates → pinned + Diun + manual.** No Watchtower, no blind auto-pull. Diun
  watches your running tags and pings ntfy when something is behind; you decide
  when to bump.

## One-time host prep

```bash
# 1. Install Docker Engine + compose plugin (idempotent)
sudo ./foss-setup/scripts/setup/install-docker-ubuntu.sh

# 2. Shared proxy network so Caddy can reach services by container name
docker network create edge

# 3. Stacks directory (Dockge convention)
sudo mkdir -p /opt/stacks
sudo cp -r stacks/* /opt/stacks/    # or: git clone this repo into /opt/stacks
```

## Per-stack bring-up

Each stack folder has a `compose.yaml` and a `.env.example`. For each one:

```bash
cd /opt/stacks/<name>
cp .env.example .env        # then edit secrets
docker compose up -d
```

Recommended order: **caddy** and **ntfy** first (proxy + notifications), then
**adguard**, **dockge**, **beszel**, **uptime-kuma**, then the app stacks
(**seerr**, **miniflux**, **navidrome**), and **diun** last so it sees everything.

> Bring **Dockge** up early, then manage the rest from its web UI — it runs
> `docker compose` in each `/opt/stacks/<name>` folder for you.

## Networking model

- All web services join the external **`edge`** network. Caddy reverse-proxies to
  them by container name (e.g. `reverse_proxy seerr:5055`).
- Host ports are also published for direct LAN access (e.g. Navidrome `:4533` for
  Symfonium/Amperfy). Drop the `ports:` blocks for anything you only reach via Caddy.
- **AdGuard/Pi-hole bind host port 53** — make sure Ubuntu's `systemd-resolved`
  stub isn't already on 53 (the install script notes how to free it).

## Secrets & Git

- `.env` files hold all secrets and are git-ignored (see `.gitignore`). Only the
  `.env.example` templates are committed.
- Commit the compose files + Caddyfile so the whole box is `git clone` + `docker
  compose up` rebuildable. Back up bind-mounted `./data`/`./db`/`./conf` dirs and
  named volumes (`caddy_data`) separately — those hold state, not config.

## Updating a service (deliberate)

```bash
cd /opt/stacks/<name>
# edit compose.yaml: bump the pinned tag after reading release notes
docker compose pull
docker compose up -d
docker image prune -f   # optional cleanup
```
