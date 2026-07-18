# Reverse proxy (caddy) — routes, reloads, HA proxy path

What to do when `ha-proxy-e2e` or `mini-caddy-live-config-current` fires (ntfy
topic `verification`). Both were added by **fix-32** (quality-gate
H8/H9/H18/H19/H21/M10, 2026-07-18) after two silent proxy failures ran for
days while every liveness check stayed green:

- `ha.tabaska.us` answered **400 Bad Request** for 11 days (Jul 7–18) because
  HA had no `http.use_x_forwarded_for` / `trusted_proxies` — HA itself was
  healthy, caddy was healthy, only the *proxied* path was dead.
- the `llamaswap` vhost sat in the on-disk Caddyfile for 3 days while the
  running caddy (never reloaded) had no route or cert for it — clients got a
  TLS "internal error".

The shared lesson: **the running config, not the file on disk, serves
traffic — and the consumer path, not the backend port, is what users hit.**

## `ha-proxy-e2e` failed — ha.tabaska.us no longer serves the HA frontend

The check curls `https://ha.tabaska.us/` through caddy on the mini and expects
the real frontend HTML (`<title>Home Assistant</title>`).

1. Reproduce and classify:
   `curl -sk -i --resolve ha.tabaska.us:443:192.168.10.2 https://ha.tabaska.us/ | head -5`
   - **`400: Bad Request` with `server: … aiohttp`** — the request reached HA
     and HA rejected the proxy. The `http:` block in HA's
     `/config/configuration.yaml` is missing or wrong (lost in a
     restore/factory reset). Restore it (canonical copy:
     `foss-setup/configs/homeassistant/configuration.yaml.example`, the
     `http:` block — `use_x_forwarded_for: true`, `trusted_proxies:
     [192.168.10.2]`), then `ha core check` + `ha core restart`.
   - **TLS error / 502** — the caddy side is broken; treat as
     `mini-caddy-live-config-current` below.
   - **Direct also down** (`curl http://192.168.10.50:8123/` fails) — full HA
     outage; `ha-http` (crit) is the primary signal, follow its runbook.
2. Editing files on the HA Green (no regular SSH — LAN-only appliance, drive
   via API): the **Terminal & SSH add-on (`core_ssh`) is installed but
   STOPPED, `boot: manual`, port 22 mapped**. Start it via the Supervisor
   WebSocket proxy (`supervisor/api` command, endpoint
   `/addons/core_ssh/start`, HA token in vault `hosts.ha.api_token` — the
   REST `/api/hassio/*` proxy 401s in HA 2026.x, use the WS command), do the
   work as `root@192.168.10.50` (laptop pubkey authorized), then **stop the
   add-on again** (`/addons/core_ssh/stop`) so no SSH port stays open.

## `mini-caddy-live-config-current` failed — Caddyfile edited but never reloaded

The check adapts `/opt/stacks/caddy/caddy/Caddyfile` inside the container and
diffs the vhost set against the admin-API running config.

1. The output names the drift: `missing_live:` = vhosts on disk that caddy is
   not serving (an edit without a reload — the llamaswap failure mode);
   `extra_live:` = vhosts removed from disk but still being served.
2. Validate then reload (graceful, zero downtime):
   `ssh mini 'docker exec caddy caddy validate --config /etc/caddy/Caddyfile && docker exec caddy caddy reload --config /etc/caddy/Caddyfile'`
3. Confirm the consumer end for whatever vhost drifted:
   `curl -sk --resolve <name>.tabaska.us:443:192.168.10.2 https://<name>.tabaska.us/ -o /dev/null -w '%{http_code}\n'`
4. **Every Caddyfile edit must end with a reload** — treat
   edit-without-reload as an incomplete change, and mirror the edit to
   `foss-setup/configs/docker-stack/stacks/caddy/caddy/Caddyfile` plus the
   `/opt/stacks` git repo (anti-drift).

## Related retirements

`deptrack.tabaska.us` is intentionally dead (Dependency-Track fully retired
2026-07-11; vault creds and the stale `/opt/stacks/dependency-track` dir were
purged by fix-32). The LAN wildcard `*.tabaska.us → 192.168.10.2` makes any
unknown name resolve to caddy and fail the TLS handshake — that is normal for
retired/nonexistent names, not an incident.
