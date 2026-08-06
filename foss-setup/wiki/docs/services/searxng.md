# searxng

SearXNG — private metasearch engine (lai-01, local-ai buildout run 12).

| | |
|---|---|
| **Host** | [mini](../hosts/mini.md) |
| **URL** | https://searxng.tabaska.us |
| **Source** | `foss-setup/configs/docker-stack/stacks/searxng/compose.yaml` |
| **Notes** | Private metasearch (lai-01, local-ai buildout) — Kagi replacement + the web-search backend for Open WebUI (lai-03). JSON API enabled server-side (search.formats includes json; OWUI strips &format=json from query URLs) and limiter OFF — LAN/tailnet-only. Host port 8888 -> container 8080; browsers via Caddy. |
| **Upstream docs** | <https://github.com/searxng/searxng> · <https://docs.searxng.org> |

## About

SearXNG is the fleet's private metasearch engine (lai-01, local-ai buildout) — the self-hosted Kagi replacement and, more importantly, the web-search backend the local AI stack consumes (Open WebUI web search / Agentic Research, lai-03). It runs as `searxng/searxng:2026.8.4-c63835bd2` (a PINNED date tag — SearXNG only publishes a rolling stream, so the pin is the fleet's stability knob) on the Mac mini at `/opt/stacks/searxng`, on the shared external `edge` network for Caddy (https://searxng.tabaska.us for humans) AND published on host `:8888` (container `:8080`) so LAN API consumers — Open WebUI on the rig, the verification probe — can hit `http://192.168.10.2:8888/search?q=...&format=json` directly. Two settings are load-bearing and deliberate in `./searxng/settings.yml` (committed, secret-free, `use_default_settings: true`): `search.formats` includes `json` (without it the JSON API answers 403 Forbidden; OWUI strips any `&format=json` baked into SEARXNG_QUERY_URL, so this server-side list is the ONLY way to enable it), and `server.limiter: false` (the default limiter/bot-detection classifies plain API clients like curl/OWUI as bots and blocks them). Both are safe because this is a LAN/tailnet-only instance — nothing is port-forwarded outward. The single secret, `server.secret_key`, is injected as the `SEARXNG_SECRET` env var from the gitignored `./.env` (vault `searxng.secret_key`, template `.env.example`). No state worth backing up: `./searxng` holds config only and the `searxng_cache` volume is disposable.

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `searxng` | `searxng/searxng:2026.8.4-c63835bd2` | `8888:8080` |

## Volumes

| Service | Volume |
|---|---|
| `searxng` | `./searxng:/etc/searxng` |
| `searxng` | `searxng_cache:/var/cache/searxng` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `SEARXNG_SECRET`

## Troubleshooting

- **API queries return HTTP 403 Forbidden while the web UI works fine (Open WebUI web search fails / searxng-json-probe check fails).** — The `json` format has been dropped from `search.formats` in `/opt/stacks/searxng/searxng/settings.yml` — SearXNG 403s any `format=` its formats list does not contain. Restore `formats: [html, json]` and `cd /opt/stacks/searxng && docker compose restart`. Do NOT try to fix this from the Open WebUI side by appending `&format=json` to SEARXNG_QUERY_URL — OWUI strips that parameter; only the server-side list works.
- **API queries return HTTP 429 "Too Many Requests" or a bot-detection block page from curl/OWUI.** — The limiter got re-enabled (an image bump can also introduce new botdetection defaults). This is a private LAN instance: set `server.limiter: false` in `/opt/stacks/searxng/searxng/settings.yml` and restart the stack. If a future exposure change ever makes it public-facing, re-enable the limiter and give OWUI a bypass instead (limiter.toml token pass-through) rather than running an open unmetered instance.
- **Container exits at startup complaining about the secret key (or `server.secret_key` is still the 'ultrasecretkey' placeholder).** — `SEARXNG_SECRET` is missing/empty — the env override is how `server.secret_key` gets set (it is deliberately NOT in the committed settings.yml). Recreate `/opt/stacks/searxng/.env` from `.env.example` with the value from the vault key `searxng.secret_key`, then `docker compose up -d`.
- **Searches return zero results or only errors in the results JSON (`results: []` with engine errors in /stats).** — Individual upstream engines rate-limit or break routinely — that is why the check queries a broad term and any engine answering makes it pass. Check https://searxng.tabaska.us/stats for per-engine error rates; a single red engine is normal background noise, ALL engines failing usually means the mini lost outbound DNS/internet (check AdGuard/Unbound and the mini's uplink first). Engine fixes ride image bumps: update the pinned tag in compose.yaml (both repos) and `docker compose pull && docker compose up -d`.

## Operations

```bash
ssh mini 'cd /opt/stacks/searxng && docker compose ps'
ssh mini 'cd /opt/stacks/searxng && docker compose logs --tail 50'
ssh mini 'cd /opt/stacks/searxng && docker compose pull && docker compose up -d'
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
