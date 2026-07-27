# Household "Report a Problem" bug intake (bug-01)

A five-second way for a **non-technical** household member to report that something's
broken, without knowing any service names. A Homepage tile opens an activity-first form;
on submit it files a labeled issue in Forgejo and pings the operator.

## For the household — how to report a problem

1. Open the dashboard (**home.tabaska.us**) and tap the **🐞 Report a Problem** tile
   (top of the **Home** group), or bookmark **bug.tabaska.us** on your phone home screen.
2. Pick **what you were trying to do** (Watch, Listen, Photos, Read, …) and type **what
   happened** in your own words. That's it — hit **Submit**.
3. Everything under *Optional* (which device/room, when, how stuck, a screenshot) is
   genuinely optional — skip it if you're in a hurry.

There is nothing to install and no login. The page only works on the home Wi-Fi or the
family VPN (Tailscale) — it is not on the public internet.

## Architecture

```
 phone/laptop ──► bug.tabaska.us  (Caddy, tailnet+LAN only, NO public DNS)
                    │  redir / → /form/<webhookId> ; reverse_proxy n8n:5678
                    ▼
                  n8n  "bug-report-intake"  (/opt/stacks/journaling, :5678)
                    ├ Build issue payload   activity → service label + severity + body
                    ├ Get labels → Resolve  Forgejo label NAMES → IDs (Gitea 1.22 wants IDs)
                    ├ Create Forgejo issue  POST home/household-bugs  (source:home, service:*, sev:*)
                    ├ (screenshot?) Upload  POST issues/{n}/assets  (best-effort)
                    └ Real report? ─► ntfy 'bugs' (+ Discord if webhook set)
                                       (healthcheck-sentinel reports skip notify)
```

- **Access model:** `*.tabaska.us` has **no public DNS record**; the AdGuard split-horizon
  rewrite `*.tabaska.us → 192.168.10.2` resolves it for tailnet/LAN clients only, and the
  TLS cert comes via Cloudflare DNS-01 (no inbound port). So `bug.tabaska.us` is reachable
  on the home network / Tailscale and **nowhere else** — no spam surface. Adding a public
  A record would be caught by `edge-public-dns-no-rfc1918`.
- **Form path quirk:** n8n ignores a Form Trigger's custom `path` for CLI-imported
  workflows and serves the form at `/form/<webhookId>`. The webhookId is pinned in the
  workflow JSON (`8f2c1a4b-6d3e-4a90-b1c2-a1b2c3d4e5f6`), so the Caddy `redir` is stable.
- **Activity → service label** (coarse routing; the body lists candidate services and the
  operator re-triages): Watch→`service:plex`, Listen→`service:navidrome`, Photos→
  `service:immich`, Read→`service:komga`, Journal→`service:journaling`, Dashboard→
  `service:homepage`, Game→`service:games`, Request→`service:seerr`, else `service:triage`.

## Files (anti-drift — live + repo, same session)

| thing | live | repo mirror |
|---|---|---|
| n8n workflow | imported into `n8n` container (`/home/node/.n8n`) | `configs/docker-stack/stacks/journaling/n8n/bug-report-intake.workflow.json` |
| secrets passthrough | `/opt/stacks/journaling/.env` | `…/journaling/compose.yaml` + `.env.example` |
| Caddy vhost | `/opt/stacks/caddy/caddy/Caddyfile` (`bug.{$DOMAIN}`) | `configs/docker-stack/stacks/caddy/caddy/Caddyfile` |
| Homepage tile | `/opt/stacks/homepage/config/services.yaml` (Home group) | `configs/docker-stack/stacks/homepage/config/services.yaml` |
| checks | `/opt/verification/{checks.d/bug-intake.yaml,bin/bugreport-e2e.py}` | `foss-setup/verification/{checks.d/bug-intake.yaml,bin/bugreport-e2e.py}` |

## Secrets

- `forgejo.n8n_household_bugs_token` — least-priv token (`write:issue` + `read:repository`)
  the workflow uses to create issues + read labels. Live `.env` `FORGEJO_TOKEN`.
- `ntfy.bugs_token` — write-only publisher for topic `bugs`. Live `.env` `NTFY_TOKEN`.
- `ntfy.bugs_publisher_password` — password for the `buguser` ntfy account.
- `discord.bugs_webhook_url` — **deferred/optional**; empty ⇒ the Discord node no-ops and
  ntfy still fires. To enable: set it in the vault, mirror to live `.env`
  `DISCORD_BUGS_WEBHOOK`, then `docker compose up -d n8n`.
- `forgejo.verification_bugreport_probe_token` — `write:issue`+`write:repository` for the
  E2E probe (create-via-form + delete its own probe issue). Runner env `FORGEJO_PROBE_TOKEN`.

## Monitoring

- `bug-intake-form-armed` (fast, crit) — the form is served and the workflow is active.
- `bug-intake-homepage-tile` (fast, warn) — the household tile is present.
- `bug-intake-e2e` (daily, crit) — submits a **sentinel** report (`n8n-bugreport-probe`),
  asserts a labeled issue appears in `home/household-bugs`, then deletes it. The sentinel
  makes the workflow skip ntfy/Discord so the probe never buzzes the operator.

## Re-deploying the workflow (n8n 2.x activation dance)

```bash
# after editing bug-report-intake.workflow.json (mirror to /opt/stacks/journaling/n8n/)
docker exec n8n n8n import:workflow --input=/home/node/.n8n/bug-report-intake.workflow.json
docker exec n8n n8n publish:workflow --id=bug01reportintake
docker restart n8n            # publish takes effect only on restart
curl -s http://localhost:5678/form/8f2c1a4b-6d3e-4a90-b1c2-a1b2c3d4e5f6 | grep -q 'What happened' && echo armed
```

**Gotchas:** import *deactivates* the published version — always re-`publish`. A stale
`webhook_entity` row can survive an unpublish/re-import; clear it with n8n stopped
(`DELETE FROM webhook_entity WHERE workflowId='bug01reportintake'`). The form submit is
**multipart/form-data only** (it has a file field) — an `x-www-form-urlencoded` POST 500s.

## Troubleshooting

- **Form 404s** → workflow not active. Re-run the activation dance above.
- **Submit 500 "Expected multipart/form-data"** → the client sent urlencoded; use multipart.
- **No issue created** → check the `Create Forgejo issue` node; the token needs
  `write:issue` and the repo `home/household-bugs` + its labels must exist.
- **No ntfy** → `buguser` needs write access to topic `bugs`
  (`docker exec ntfy ntfy access buguser bugs write-only`); token in `.env` `NTFY_TOKEN`.
- **Probe curl gets 401** → an older build had the form's `ignoreBots` filter on, which
  401s non-browser user-agents; it has been removed. If it returns, drop `options.ignoreBots`.
