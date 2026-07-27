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

## Read-only auto-triage (bug-02) — "mini is the eyes, rig is the brain"

When an issue is filed, the same n8n workflow runs a second branch that gathers
**read-only** evidence and asks the rig LLM for a plain-English diagnosis, posted back as
an issue comment. The split is **security-by-construction** (operator decision
2026-07-27), not a policy toggle:

```
 Create Forgejo issue ─┬─► (notify branch: ntfy / Discord)
                       ├─► (screenshot upload branch)
                       └─► Prep triage ─► Run triage? ─► Gather evidence ─► Build prompt
                                                              │                    │
                        bug-triage-evidence  ◄────────────────┘                    ▼
                        (mini, docker.sock:ro + HTTP probes)             Call LiteLLM (rig :4000)
                                                                                   │
                        Post triage comment  ◄── Build triage comment ◄────────────┘
                        + label `triaged`
```

- **The eyes never mutate; the brain has no hands.** Evidence-gathering runs on the mini,
  which already has read-only docker for its own containers + tailnet reach to curl every
  other host's API. The `bug-triage-evidence` sidecar mounts the docker socket **read-only
  and uses it GET-only** (container state/health + recent logs), plus unauthenticated
  health probes of the mapped service (works cross-host by LAN IP). It holds **no secrets**,
  drops all caps, runs a read-only rootfs, and is **internal only** (no host port, no Caddy
  vhost). The rig is reached **only** via LiteLLM :4000 (a least-priv virtual key scoped to
  the `utility` model) — pure inference, zero fleet access, no new SSH trust.
- **The read-only ceiling is structural.** The comment is diagnosis + likely cause +
  confidence only — never a restart, a fix, or a suggested command. Every comment carries a
  READ-ONLY footer stating no fleet state was changed.
- **Expected-state aware.** Each per-service playbook separates `context` (background) from
  `expected_states` (documented normal conditions that can *cause* a symptom — e.g. the
  Immich ML **night-window**, the rig LLM GPU-contention degrade). The prompt may answer
  "expected, not a fault" **only** when an `expected_states` entry actually explains the
  report, so a normal state (daytime Immich ML off) is not misdiagnosed as the bug.
- **Best-effort / degrade, don't fail.** v1 is single-shot (evidence in → prose out), model
  = `utility`/fast. If the reasoning model is unavailable (rig GPU contention), the pipeline
  still posts an **evidence-only** comment noting the degrade — a SKIP, not a failure.
- **Activity → probe service key** reuses the bug-01 label map (`service:immich` →
  `immich`, etc.). The bug-01 form-armed sentinel (`n8n-bugreport-probe`) skips triage; the
  bug-02 sentinel (`n8n-triage-probe`) runs it (so the E2E exercises the full loop).
- **Future upgrade (deferred):** an agentic loop that *chooses* which probes to run would
  need a read-only key back on the rig; v1 deliberately keeps the rig hands-free. Widening
  the triage key to a larger model group (a one-line key edit) is the other easy upgrade —
  by day the rig GPU is free (Immich ML is night-gated) so a bigger model could load.

## Files (anti-drift — live + repo, same session)

| thing | live | repo mirror |
|---|---|---|
| n8n workflow | imported into `n8n` container (`/home/node/.n8n`) | `configs/docker-stack/stacks/journaling/n8n/bug-report-intake.workflow.json` |
| triage evidence sidecar | `bug-triage-evidence` (`/opt/stacks/journaling/bug-triage/`) | `configs/docker-stack/stacks/journaling/bug-triage/evidence-server.py` + `compose.yaml` |
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
- `ai_stack.litellm_bug_triage_key` — **bug-02** least-priv LiteLLM virtual key (scoped to
  the `utility` model group) for the triage reasoning call. Live `.env` `LITELLM_TRIAGE_KEY`.
  Minted via `litellm.master_key`; the evidence sidecar itself needs **no** secret.

## Monitoring

- `bug-intake-form-armed` (fast, crit) — the form is served and the workflow is active.
- `bug-intake-homepage-tile` (fast, warn) — the household tile is present.
- `bug-intake-e2e` (daily, crit) — submits a **sentinel** report (`n8n-bugreport-probe`),
  asserts a labeled issue appears in `home/household-bugs`, then deletes it. The sentinel
  makes the workflow skip ntfy/Discord so the probe never buzzes the operator.
- `bug-triage-evidence-armed` (fast, warn) — the read-only evidence sidecar is `healthy`.
- `bug-triage-e2e` (daily, warn) — submits a triage sentinel (`n8n-triage-probe`) report,
  asserts an **auto-triage comment** appears on the issue carrying the read-only footer +
  `triaged` label, then deletes the issue. **Degrade-aware:** a real diagnosis →
  `BUGTRIAGE_OK`; an evidence-only degrade (model contended) → `BUGTRIAGE_SKIP_MODEL_UNAVAILABLE`
  (both PASS); no comment at all → `BUGTRIAGE_FAIL` (loop broken).

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
