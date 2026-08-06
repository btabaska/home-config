# SearXNG (private metasearch / AI web-search backend)

Runbook for the `searxng-json-probe` verification check and general operation of
**SearXNG** — the fleet's private metasearch engine (lai-01, local-ai buildout).
Service page: [searxng](../services/searxng.md).

- **Host:** Mac mini (`192.168.10.2`), Docker, stack `/opt/stacks/searxng` (project `searxng`)
- **URLs:** <https://searxng.tabaska.us> (humans, via Caddy) · `http://192.168.10.2:8888` (LAN API consumers — Open WebUI on the rig, verification)
- **Compose:** live `/opt/stacks/searxng/compose.yaml`; repo mirror `foss-setup/configs/docker-stack/stacks/searxng/`
- **Image:** `searxng/searxng:2026.8.4-c63835bd2` (pinned date tag — SearXNG only publishes a rolling stream, the pin is the stability knob)
- **Config:** `./searxng/settings.yml` (committed, secret-free; `use_default_settings: true`)
- **Secrets:** `SEARXNG_SECRET` (= `server.secret_key`) in the gitignored `./.env`; vault `searxng.secret_key`; template `.env.example`
- **State:** none worth backing up — `./searxng` is config only, the `searxng_cache` volume is disposable

## The two load-bearing settings

Both live in `settings.yml` and exist for the downstream **Open WebUI** consumer (lai-03):

1. **`search.formats: [html, json]`** — the JSON API (`GET /search?q=...&format=json`).
   SearXNG answers **403 Forbidden** for any `format=` not in this list. OWUI *strips*
   any `&format=json` baked into `SEARXNG_QUERY_URL`, so the server-side list is the
   **only** way to enable JSON — do not chase this from the OWUI side.
2. **`server.limiter: false`** — the default limiter/bot-detection classifies plain API
   clients (curl, OWUI) as bots and blocks them (429/block page). This is a private
   LAN/tailnet-only instance (no WAN exposure), so the limiter is off. If it is ever
   made public-facing, re-enable the limiter and give OWUI a token pass-through instead.

## The consumer check

`searxng-json-probe` (in `verification/checks.d/local-ai.yaml`) probes the consumer path,
not liveness: it calls `http://127.0.0.1:8888/search?q=...&format=json` from the mini —
the exact call shape OWUI makes — and requires a **non-empty `results` array**. A 403
(json dropped from formats), a 429 (limiter re-enabled), or an all-engines-dead empty
result set all fail it. One shell-level retry with a second query rides out a single
flaky engine sweep. Container liveness/manifest is covered separately by
`containers-manifest-mini` / `containers-health-mini` in `docker-fleet.yaml`.

Run it in isolation from the mini (audit-safe):

```
ssh mini 'mkdir -p /tmp/lac && cp /opt/verification/checks.d/local-ai.yaml /tmp/lac/ && \
  VERIFICATION_STATE_DIR=/tmp/las python3 /opt/verification/bin/checks_runner.py \
  --checks-dir /tmp/lac --no-notify --json; rm -rf /tmp/lac /tmp/las'
```

## Troubleshooting

- **JSON API returns 403 while the web UI works.** `json` fell out of `search.formats`
  in `/opt/stacks/searxng/searxng/settings.yml`. Restore `formats: [html, json]`, then
  `cd /opt/stacks/searxng && docker compose restart`. Mirror the edit back to
  `foss-setup/configs/docker-stack/stacks/searxng/` (anti-drift).
- **429 / bot-block page from curl or OWUI.** The limiter got re-enabled (an image bump
  can introduce new botdetection defaults). Set `server.limiter: false` and restart.
- **Startup failure mentioning the secret key.** `SEARXNG_SECRET` is missing — recreate
  `./.env` from `.env.example` with the vault value `searxng.secret_key`, then
  `docker compose up -d`.
- **`results: []` for every query.** All upstream engines failing usually means the mini
  lost outbound DNS/internet — check AdGuard/Unbound and the uplink first. Per-engine
  error rates: <https://searxng.tabaska.us/stats>. A single red engine is normal noise.
- **Upgrading.** Pick a current date tag (`https://hub.docker.com/r/searxng/searxng/tags`),
  bump `compose.yaml` in **both** repos, `docker compose pull && docker compose up -d`,
  then confirm `searxng-json-probe` still passes (engine plumbing changes ride upstream
  bumps).

## Open WebUI wiring (lai-03 — later item)

When OWUI is pointed here: engine `searxng`, query URL
`http://192.168.10.2:8888/search?q=<query>` (**no** `&format=json` suffix — stripped
anyway; the server-side formats list above is what makes JSON work), bypass embedding ON,
concurrency > 0.
