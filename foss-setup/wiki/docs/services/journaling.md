# journaling

Self-hosted AI journaling stack (journal-01) — LAN/tailnet only, no cloud.

| | |
|---|---|
| **Host** | [mini](../hosts/mini.md) |
| **URL** | https://memos.tabaska.us |
| **Source** | `foss-setup/configs/docker-stack/stacks/journaling/compose.yaml` |
| **Notes** | Self-hosted AI journaling stack (journal-01): Memos front-end (:5230, memos.tabaska.us) + n8n automation (:5678, n8n.tabaska.us) + faster-whisper/speaches (:8010, internal only). Reflections come from rig llama-swap model dolphin-venice-24b. LAN/tailnet only, no cloud. Analyze workflow + tokens wired in journal-02..06. |
| **Upstream docs** | <http://192.168.10.12:9292> |

## About

A fully LAN-local AI journaling stack on `mini` at `/opt/stacks/journaling/` (mirrored to `foss-setup/configs/docker-stack/stacks/journaling/`), stood up by task `journal-01`. Three digest-pinned containers: **Memos** (`neosmemo/memos:0.29.1`, host `:5230`, fronted by Caddy at https://memos.tabaska.us) is the journal front-end; **n8n** (`n8nio/n8n:2.32.2`, host `:5678`, https://n8n.tabaska.us) is the automation layer that will react to each new entry; and **faster-whisper** via Speaches (`ghcr.io/speaches-ai/speaches:0.8.3-cpu`, host `:8010`) is the internal-only server-side dictation endpoint — deliberately given NO Caddy vhost. Inference is NOT local to this stack: n8n calls the rig's llama-swap at `http://192.168.10.12:9292/v1/chat/completions` with model `dolphin-venice-24b` (temp ~0.35, an uncensored-but-steerable coach), because the mini has no GPU and the capable models live behind llama-swap, not the small-model Ollama `:11434`. faster-whisper runs on CPU for the same reason (the fleet's only GPU, the rig 3090 Ti, is pinned to LLM + Immich ML). All state (Memos sqlite/uploads, n8n workflows/encryption-key) is bind-mounted under the stack dir so restic backs it up. Ports 5230/5678/8010 were chosen because `:8000`/`:8080` are already taken on the mini. Whole stack is LAN/tailnet only, no public exposure and no cloud/telemetry (n8n diagnostics + version checks disabled); the single outbound call is faster-whisper's one-time model pull from HuggingFace. `journal-01` stood up the scaffold; `journal-02` wired the event pipe: the host Memos account (`btabaska`, creds at vault `journaling.memos.*`), a never-expiring Personal Access Token (`memos_pat_…`, vault `journaling.memos.api_token`, also in the live `.env` as `MEMOS_API_TOKEN` for n8n), and a Memos webhook on **every** memo event → the n8n container URL `http://n8n:5678/webhook/journal`. Memos runs with `--allow-private-webhooks` (compose `command`) so it may POST to that private container name; public user-registration was closed (`instance/settings/GENERAL.disallowUserRegistration=true`). A live memo was confirmed to deliver a `memos.memo.created` event to n8n. The validated 0.29 payload/API shapes are recorded in `docs/journaling-stack-plan.md`. `journal-03` built the **`journal-analyze`** n8n workflow (in `n8n/journal-analyze.workflow.json`) that now owns `POST /webhook/journal`, superseding the `journal-webhook-probe` (kept but deactivated). Its pipeline: webhook → a loop-safe **Guard** (Code node) that proceeds only on `memos.memo.created` events carrying a `#journal` tag and never on its own output — it drops `memos.memo.comment.created` outright and skips any memo whose content starts with the `🧭 **Reflection**` sentinel or carries `#analyzed` (essential, because writing a comment fires **two** events both carrying the comment memo) → an **HTTP** call to the rig coach model (120 s timeout, 3 retries, continue-on-error) → a **tolerant JSON parse/repair** (strips ``` fences, grabs the first `{…}`, and closes a truncated object) so a chatty small-model reply never breaks the loop → **write-back as a Memos COMMENT** (`POST /api/v1/memos/{name}/comments`, never a body edit — that would re-fire the webhook) formatted `🧭 **Reflection** · mood N/10 · sentiment` + emotions/themes + one gentle nudge. A VRAM-evicted/OOM'd model just yields no comment (best-effort; the entry is always saved). The workflow reads `MEMOS_API_TOKEN`/`LLM_MODEL`/`LLM_BASE_URL`/`LLM_TEMP` from the n8n container env via `$env`, so swapping the coach model (e.g. to `deckard-heretic`) is a one-line `.env` change + `docker compose up -d n8n`. Validated end-to-end: a `#journal` and a `#gamelog` entry each produced exactly one reflection comment with the two comment-triggered events skipped by the guard. `templates/daily.md` and `templates/gamelog.md` (both carry `#journal`) ship in the stack dir. Still to come: the transcription branch (`journal-04`), the Open WebUI coach preset (`journal-05`) and the README + end-to-end monitoring closeout (`journal-06`).

## Containers

| Service | Image (pinned) | Ports |
|---|---|---|
| `memos` | `neosmemo/memos:0.29.1@sha256:3e1253477066eb2aefa91145f7f9038bb931ed88c8a3ee05310a933594cdba7d` | `5230:5230` |
| `n8n` | `n8nio/n8n:2.32.2@sha256:119afa425cc1ac3e62823c65aae16fcee409ef4c94555ebab3a9dff6eccb9073` | `5678:5678` |
| `faster-whisper` | `ghcr.io/speaches-ai/speaches:0.8.3-cpu@sha256:21e3df06d842fb7802ab470dd77c25f0e8c0d22950e8d8c6ae886e851af53ef8` | `8010:8000` |

## Volumes

| Service | Volume |
|---|---|
| `memos` | `./memos:/var/opt/memos` |
| `n8n` | `./n8n:/home/node/.n8n` |
| `faster-whisper` | `./whisper-cache:/home/ubuntu/.cache/huggingface` |

## Environment (`.env`)

Variable names from `.env.example` — real values live in `.env` on the host, sourced from the vault (never committed):

- `TZ`
- `N8N_HOST`
- `N8N_WEBHOOK_URL`
- `RIG_IP`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TEMP`
- `MEMOS_API_TOKEN`

## Troubleshooting

- **Journal entries save fine but no reflection comment ever appears.** — Reflections depend on the rig, which is a separate host. Confirm the coach model is reachable and registered: `curl -s http://192.168.10.12:9292/v1/models | grep dolphin-venice-24b` (the `journaling-coach-model-reachable` verification check does this). llama-swap loads the ~17 GB model on first call and a rig "gaming force-unload" hook can evict it (Immich ML also holds ~12 GB of the 24 GB card), so analysis is best-effort — the entry is always saved regardless, and the `journal-analyze` workflow retries 3× then posts nothing rather than erroring. Also confirm the workflow is armed (the `journaling-analyze-armed` check: `curl -s http://localhost:5678/webhook/journal` must reply `…not registered for GET requests`, which n8n returns only when a POST webhook actually owns that path).
- **Memos entries are created but n8n never receives a webhook (no executions).** — Check the wiring the `journaling-memos-webhook-wired` verification check guards: the Memos webhook must still point at `http://n8n:5678/webhook/journal` — `curl -s -H "Authorization:Bearer $MEMOS_API_TOKEN" http://localhost:5230/api/v1/users/btabaska/webhooks` (token in `/etc/verification/env`). Memos silently drops private-IP webhook targets unless it runs with `--allow-private-webhooks` (compose `command:` on the `memos` service) — verify with `docker inspect memos --format '{{json .Config.Cmd}}'`. On the n8n side the receiving workflow must be **active AND published**: n8n 2.x needs a *published version* (`docker exec n8n n8n publish:workflow --id=<id>`) — a bare `active=1` flag alone registers nothing (boot logs "Processed 0 published workflows") — then a **restart** to register. Two traps: (1) the CLI `unpublish`/re-`import` leaves a stale `webhook_entity` row that makes the next workflow fail activation with "URL path … already taken" — clear it with n8n stopped (`DELETE FROM webhook_entity WHERE workflowId='<old-id>'`, then start); (2) `import:workflow` deactivates the published version, so re-`publish` after every import. The `journaling-analyze-armed` check catches a silently-unregistered webhook. Note n8n uses SQLite WAL — when reading executions off disk, copy `database.sqlite` **and** its `-wal`/`-shm` files or recent rows are invisible.
- **memos.tabaska.us or n8n.tabaska.us returns a TLS/connection error right after a deploy.** — Both are new Caddy vhosts on the mini `edge` network. Confirm Caddy reloaded after the Caddyfile edit (`docker exec caddy caddy reload --config /etc/caddy/Caddyfile`) and that both containers are on the `edge` network (`docker inspect memos --format '{{json .NetworkSettings.Networks}}'`). A cold first request can 000 while the cert warms; retry once.
- **One of the three containers is unhealthy or the healthcheck.sh reports DEGRADED.** — Run the stack healthcheck from the mini: `ssh mini 'cd /opt/stacks/journaling && ./scripts/healthcheck.sh'` — it probes Memos `:5230/healthz`, n8n `:5678/healthz`, faster-whisper `:8010/health` and rig `:9292/v1/models`. For a stuck container, `cd /opt/stacks/journaling && docker compose logs --tail 50 <service>` then `docker compose up -d`. n8n and whisper bind-mount dirs must stay owned by uid 1000.

## Operations

```bash
ssh mini 'cd /opt/stacks/journaling && docker compose ps'
ssh mini 'cd /opt/stacks/journaling && docker compose logs --tail 50'
ssh mini 'cd /opt/stacks/journaling && docker compose pull && docker compose up -d'
```

Update procedure: [Runbooks → Update images](../runbooks/update-images.md). Full add/change loop: [Runbooks → Add a service](../runbooks/add-a-service.md).

*Generated by `scripts/docs/gen-wiki-services.py` — do not edit by hand; edit the compose file and regenerate.*
