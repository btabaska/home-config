# Retro Cable (tv.home.tabaska.us)

Retro Cable (retro-cable-01, 2026-11-01): Bay Area cable TV as it was on today's
date in any year 1990–2010 — a browser SPA plus a deterministic scheduling API.
**https://tv.home.tabaska.us** (LAN only), also on the Homepage **Media** group.

It is **not** an `/opt/stacks` stack. Its own private repo
(`btabaska/retro-cable`) owns the compose, deploy and rollback; this repo only
owns the Caddy vhost, the Homepage tile, the catalog row and the checks.

## What it's wired to

```
LAN browser ── tv.home.tabaska.us (AdGuard *.tabaska.us wildcard → mini .2)
   └─▶ caddy (local_tls, abort if not private_ranges)
         └─▶ retro-cable-web:80   (edge network alias; Caddy file_server SPA, proxies /api)
               └─▶ retro-cable-api-1 :8000 (retro-cable_default network)
```

| thing | where |
|-------|-------|
| checkout | mini `/opt/retro-cable` (branch `ops/mini-deploy` until retro-cable PR #3 merges, then `main`) |
| compose | `/opt/retro-cable/ops/compose.yml` (+ `compose.build.yml` when building from source) |
| host settings | `/opt/retro-cable/ops/.env` — `RC_WEB_PORT=8095` (published on **127.0.0.1 only**), `RC_DATA_DIR`, `RC_MEDIA_DIR`, `RC_IMAGE_SOURCE` |
| data | `/opt/retro-cable-data` (DB) — **not** in mini restic `BACKUP_PATHS` (empty as of 2026-11-01; add it once it holds state) |
| containers | `retro-cable-api-1`, `retro-cable-web-1` (in `verification/coverage/mini.containers`) |
| vhost | Caddyfile block `tv.home.tabaska.us` — source of truth is retro-cable `ops/caddy/retro-cable.caddy`; keep the two identical |

The `:8095` loopback publish is deliberately absent from
`verification/assets/expected-listeners/mini.ports`: the listener-drift
baseline only tracks all-interface binds.

## Deploy / roll back

```bash
ssh mini
cd /opt/retro-cable && git pull                       # on the deployed branch
ops/deploy.sh sha-$(git rev-parse --short=7 HEAD)     # snapshot DB, pull/build, start, smoke, auto-rollback on failure
ops/rollback.sh                                       # restore previous version + its DB snapshot
```

`RC_IMAGE_SOURCE=build` builds images from the checkout (the GHCR packages are
private). Once a `read:packages` PAT is in the vault and `docker login ghcr.io`
is done as btabaska on the mini, drop that line from `ops/.env` so deploys pull.

Never recreate the `caddy` container for a vhost change — edit the Caddyfile
in place (it is a single-file bind mount; `sed -i` breaks the inode), then:

```bash
docker exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker exec caddy caddy reload   --config /etc/caddy/Caddyfile --adapter caddyfile
```

## Checks

Both run from the mini through the real consumer path (AdGuard → Caddy TLS →
web → API), in `verification/checks.d/mini-services.yaml`:

- `retro-cable-health` (fast tier) — `/api/health` returns `"status":"ok"`.
- `retro-cable-version` — `/api/version` parses with a version and a ≥7-char
  commit, and `/` serves the SPA shell (`id="root"`).

## Troubleshooting

- **502 from tv.home** — `docker ps | grep retro-cable`; confirm Caddy can
  reach it: `docker exec caddy wget -qO- http://retro-cable-web/api/version`.
  If that fails, the web container lost its `edge` network alias — redeploy
  with `ops/deploy.sh`.
- **Connection reset / empty reply** — you are not on a private range (the
  `@not_lan` matcher aborts). Expected off-LAN. Never add a port forward.

- **`/api/health` ok but `/api/version` fails** — the API is up but the
  build is broken or stale; check `docker logs retro-cable-api-1` and roll back.
- **Cert error** — `local_tls` is Let's Encrypt via Cloudflare DNS-01; check
  `docker logs caddy | grep tv.home`.

!!! warning "LAN-only is LAN + tailnet in practice"
    Caddy publishes :443 through docker-proxy, so requests arriving on the
    mini's **tailnet** address (100.x / fd7a:…) reach Caddy with source
    `172.25.0.1` (the `edge` bridge gateway) — inside `private_ranges` — and
    the abort does **not** fire (verified 2026-11-01). WAN is genuinely closed
    (no :443 forward, no public DNS). Real LAN clients keep their IP. To make
    it strictly LAN, change the matcher to `not remote_ip 192.168.10.0/24` in
    retro-cable `ops/caddy/retro-cable.caddy` **and** here, or disable the
    docker userland proxy on the mini (4–7AM window).
