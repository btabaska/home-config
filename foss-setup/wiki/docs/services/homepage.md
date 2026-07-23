# homepage

Homepage — the household front door + dashboard/observability layer

| | |
|---|---|
| **Host** | [mini](../hosts/mini.md) |
| **URL** | https://home.tabaska.us |
| **Source** | `foss-setup/configs/docker-stack/stacks/homepage/compose.yaml` |
| **Notes** | This dashboard. Container port 3000. |
| **Upstream docs** | <https://gethomepage.dev/> · <https://gethomepage.dev/installation/#homepage_allowed_hosts> |

## About

Homepage (gethomepage.dev) is the household's single pane of glass — the "front door" at https://home.tabaska.us that gives the family friendly app tiles (Plex, Immich, Calibre-Web, Seerr) and the operator a live observability view (Beszel, Uptime Kuma, plus the *arr stack). It runs as one container `ghcr.io/gethomepage/homepage:v1.13.2` on `mini` from `foss-setup/configs/docker-stack/stacks/homepage/compose.yaml`, listening on 3000 in-container and published as host port `3010` (deliberately not 3000/3001 to avoid clashing with Forgejo and Uptime-Kuma on the same box), also fronted by Caddy at `home.tabaska.us`. Live service widgets are lit up by `HOMEPAGE_VAR_*` secrets sourced from the vault into `.env` and referenced as `{{HOMEPAGE_VAR_*}}` in `config/services.yaml`; the container uses `dns: 192.168.10.4` (the **NAS** AdGuard — the mini's own AdGuard at .2 times out from inside containers, net-16) so `*.tabaska.us` rewrites resolve for ping/widgets. As of **home-06 (2026-07-22)** the key-needing tiles for already-running services are live-data widgets rather than plain ping tiles: Healthchecks, Paperless-ngx, Mealie (`version: 2`), Miniflux, Calibre-Web, Stash, Deluge, slskd, Forgejo (via the `gitea` widget) and Navidrome. Five creds came straight from the vault (`healthchecks.api_key`, `miniflux.api_key`, `deluge.password`, `soulseek.slskd_api_key`, `calibre-web.*`); four tokens were minted (Paperless `/api/token/`, Mealie `/api/users/api-tokens`, Forgejo `generate-access-token` scoped `read:notification,read:repository,read:issue`, Stash GraphQL `generateAPIKey`) and Navidrome's Subsonic `salt`+`token` (md5(password+salt)) derived — all stashed under vault `homepage_widgets.*`. As of **home-07 (2026-07-22)** a **Fleet** group adds per-HOST vitals — three `beszel` widget tiles (mini / rig / nas, `version: 2`, `systemId` = the exact Beszel UI name) that read live CPU/RAM/disk/network from the existing beszel hub at `http://beszel:8090` using the hub superuser (`HOMEPAGE_VAR_BESZEL_USER`/`HOMEPAGE_VAR_BESZEL_PASS` map to vault `beszel.admin_user`/`beszel.admin_password`) — reusing the beszel-agent already on every box, so zero new daemons on the 8 GB mini. The single `disk` field is each host's aggregate; the NAS `/volume1,2,3` per-mount split lives in the Beszel dashboard via the agent's `/extra-filesystems` mounts. As of **home-08 (2026-07-22)** a **Calendar** group sits first as the household's daily-use anchor: one `calendar` widget in `view: agenda` that merges upcoming Sonarr/Radarr/Lidarr releases (each an `integrations:` entry referencing the existing *arr service widget by `service_group: Media Automation` + `service_name` — it reuses that widget's url/key, so **no new *arr secret**) with personal events from a published **Proton Calendar** `.ics` feed (`type: ical`, `url: {{HOMEPAGE_VAR_PROTON_CAL_ICS}}` from vault `homepage_widgets.proton_calendar_ics_url`). Because that share link is an external dependency that can silently blank the personal half, the `homepage-calendar-ics-fetch` check has the homepage container itself `wget` the `.ics` (URL read from its own env, so no secret in the check) and assert a `BEGIN:VCALENDAR` body. As of **home-08 completion (2026-07-23)** the paired **UniFi Network** tile is live in the **Infrastructure** group: a `unifi` widget (`url: https://192.168.10.1`, fields `wan`/`lan_users`/`wlan_users`/`uptime`) that reads the UDM/Dream Wall gateway through a DEDICATED **local read-only** Network account (View Only role; vault `unifi_network.username`/`password` → `HOMEPAGE_VAR_UNIFI_USER`/`HOMEPAGE_VAR_UNIFI_PASS`) — the `unifi_protect` account 403s on the Network login API so it could not be reused. The widget handles the UniFi-OS `/proxy/network` routing and self-signed cert internally. Because a deleted / disabled / rotated account silently blanks the tile to `-` (no dead tile, no DNS error, so the `homepage-dead-tiles`/`homepage-widget-errors` guards miss it), the `homepage-unifi-tile` check drives the SAME server-side `stat/sites` path the widget uses (`/opt/verification/bin/homepage-unifi-tile.py`) and requires a real UniFi site-health payload back — it does not assert `wan == ok`, so a genuine internet outage does not flap it. Docker socket auto-discovery is intentionally DISABLED (home-03, 2026-07-07) — every tile is defined manually in `config/services.yaml` because the entrypoint drops to `PUID:PGID` and sheds groups, so the socket mount only produced repeating EACCES errors; the `/var/run/docker.sock:ro` mount remains but `config/docker.yaml` has no `local:` block.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `homepage` | `ghcr.io/gethomepage/homepage:v1.13.2` | `3010:3000` |

## Volumes

| Service | Volume |
|---|---|
| `homepage` | `./config:/app/config` |
| `homepage` | `/var/run/docker.sock:/var/run/docker.sock:ro` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `PUID`
- `PGID`
- `TZ`
- `HOMEPAGE_ALLOWED_HOSTS`
- `HOMEPAGE_VAR_SONARR_KEY`
- `HOMEPAGE_VAR_RADARR_KEY`
- `HOMEPAGE_VAR_LIDARR_KEY`
- `HOMEPAGE_VAR_READARR_KEY`
- `HOMEPAGE_VAR_BOOKSHELF_KEY`
- `HOMEPAGE_VAR_PROWLARR_KEY`
- `HOMEPAGE_VAR_PLEX_TOKEN`
- `HOMEPAGE_VAR_JELLYFIN_KEY`
- `HOMEPAGE_VAR_TAUTULLI_KEY`
- `HOMEPAGE_VAR_QBITTORRENT_USER`
- `HOMEPAGE_VAR_QBITTORRENT_PASS`
- `HOMEPAGE_VAR_IMMICH_KEY`
- `HOMEPAGE_VAR_SEERR_KEY`
- `HOMEPAGE_VAR_ADGUARD_USER`
- `HOMEPAGE_VAR_ADGUARD_PASS`
- `HOMEPAGE_VAR_HA_TOKEN`
- `HOMEPAGE_VAR_UPTIMEKUMA_SLUG`
- `HOMEPAGE_VAR_DEPTRACK_KEY`
- `HOMEPAGE_VAR_PALWORLD_ADMIN`
- `HOMEPAGE_VAR_HEALTHCHECKS_KEY`
- `HOMEPAGE_VAR_PAPERLESS_KEY`
- `HOMEPAGE_VAR_MEALIE_KEY`
- `HOMEPAGE_VAR_MINIFLUX_KEY`
- `HOMEPAGE_VAR_CALIBREWEB_USER`
- `HOMEPAGE_VAR_CALIBREWEB_PASS`
- `HOMEPAGE_VAR_ABS_KEY`
- `HOMEPAGE_VAR_KOMGA_USER`
- `HOMEPAGE_VAR_KOMGA_PASS`
- `HOMEPAGE_VAR_STASH_KEY`
- `HOMEPAGE_VAR_DELUGE_PASS`
- `HOMEPAGE_VAR_SLSKD_KEY`
- `HOMEPAGE_VAR_FORGEJO_KEY`
- `HOMEPAGE_VAR_SYNCTHING_HUB_KEY`
- `HOMEPAGE_VAR_NAVIDROME_USER`
- `HOMEPAGE_VAR_NAVIDROME_SALT`
- `HOMEPAGE_VAR_NAVIDROME_TOKEN`
- `HOMEPAGE_VAR_BESZEL_USER`
- `HOMEPAGE_VAR_BESZEL_PASS`
- `HOMEPAGE_VAR_PROTON_CAL_ICS`
- `HOMEPAGE_VAR_UNIFI_USER`
- `HOMEPAGE_VAR_UNIFI_PASS`

## Troubleshooting

- **Page won't load with "Host validation failed" after adding a new hostname or port.** — Since v1.0 `HOMEPAGE_ALLOWED_HOSTS` is a required exact-match allowlist. Add the verbatim `host:port` (and the Caddy subdomain) you type in the browser to `HOMEPAGE_ALLOWED_HOSTS` in `.env` on mini, e.g. `home.tabaska.us,192.168.10.2:3010,localhost:3010`, then `ssh mini 'cd /opt/stacks/homepage && docker compose up -d'`.
- **Logs spam `<httpProxy> Error calling http://maintainerr:6246/ ... getaddrinfo EAI_AGAIN maintainerr` (500).** — A `services.yaml` widget points at the bare container name `maintainerr`, but that container isn't on the `edge` network so Docker/AdGuard DNS can't resolve it. Either put maintainerr on the `edge` network, use its LAN IP/Caddy hostname in the widget href+url, or remove the widget block. Non-fatal — only that one tile's live status is broken.
- **Widget shows a plain link tile instead of live stats, or shows an auth error.** — The matching `HOMEPAGE_VAR_*_KEY`/`_TOKEN` in `.env` is blank or stale. Fill it from the vault and `docker compose up -d`. Blank values intentionally degrade to a plain link tile rather than erroring.
- **Backend logs show `<validateWidgetData> Invalid data for widget '<stash|calibreweb|paperlessngx>' endpoint 'undefined'` or `<credentialedProxyHandler> HTTP Error 404 calling http://<miniflux|mealie|healthchecks|slskd>/<base>/` right after a page load.** — Benign — do NOT chase it. Those widget types make one initial call to the API's *base* path (endpoint resolves to `undefined`), which 404s or returns the service's HTML login page, then fetch the real field endpoints successfully; the tile still renders live data (verified in-browser home-06 2026-07-22). The `homepage-widget-errors` check deliberately only alerts on `EAI_AGAIN`/`getaddrinfo` (a genuinely unresolvable dead tile), so this 404 noise never pages.
- **Wanting Docker container auto-discovery back.** — It is disabled by design — the app runs as PUID:PGID and can't read the socket even with group_add, producing EACCES spam. To re-enable, front the socket with docker-socket-proxy and point `config/docker.yaml` at a `tcp://` endpoint instead of the raw `/var/run/docker.sock`.

## Operations

```bash
ssh mini 'cd /opt/stacks/homepage && docker compose ps'
ssh mini 'cd /opt/stacks/homepage && docker compose logs --tail 50'
ssh mini 'cd /opt/stacks/homepage && docker compose pull && docker compose up -d'
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
