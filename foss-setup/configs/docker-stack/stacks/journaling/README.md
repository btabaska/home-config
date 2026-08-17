# Journaling stack — self-hosted, LAN-only AI journaling

Memos (journal front-end) + n8n (automation) + faster-whisper (server-side dictation), with
the coaching LLM running on the **rig** (not in this stack). You write a `#journal` entry in
Memos; n8n reacts to the `memo.created` webhook, asks the rig coach model for a short gentle
reflection, and writes it back as a **comment** on the entry (never editing your text). An
optional Open WebUI front-end on the rig lets you have a free-form coaching chat and save it
back into the journal.

**Everything is LAN/tailnet only — no cloud, no telemetry.** The one outbound call the stack
ever makes is faster-whisper's one-time model download from HuggingFace.

- **Lives on:** `mini` at `/opt/stacks/journaling/` (this repo is the mirror at
  `foss-setup/configs/docker-stack/stacks/journaling/` — edit both, same session; a host-only
  change reverts on the next redeploy).
- **Design source of truth:** `foss-setup/docs/journaling-stack-plan.md`.
- **Wiki (deep prose):** `wiki/docs/services/journaling.md` (generated — never hand-edit; edit
  `configs/docker-stack/service-enrichment.yaml`).
- **Built by tasks:** `journal-01` (scaffold) → `journal-02` (token + webhook) → `journal-03`
  (analyze workflow + loop guard) → `journal-04` (Whisper branch) → `journal-05` (OWUI
  front-end) → `journal-06` (this README + monitoring/backup closeout) → `journal-07`
  (IGDB #gamelog enrichment, opt-in) → `journal-08` (Memos native in-editor dictation) →
  `journal-09` (agent access via the built-in Memos MCP server).

## Architecture

```
 you write / dictate ─► Memos (#journal)         :5230   memos.tabaska.us
                          │ webhook memo.created (--allow-private-webhooks)
                          ▼
                        n8n  "journal-analyze"    :5678   n8n.tabaska.us
                          ├ Guard: only memo.created carrying #journal; DROP comment
                          │        events + its own 🧭 reflections  (loop prevention)
                          ├ (audio attachment?) ─► faster-whisper /v1/audio/transcriptions
                          │                          :8010→:8000  (internal, no vhost)
                          ├ LLM  ─► rig llama-swap  192.168.10.12:9292
                          │        model dolphin-venice-24b, temp 0.35  (best-effort)
                          └ write-back ─► COMMENT on the source memo (🧭 Reflection …)
 Open WebUI (rig, ai.tabaska.us): "Journaling Coach" preset + "Save to Journal" action
                          └► POST Memos /api/v1/memos as #journal ─► re-enters the loop
```

| service | image (digest-pinned) | host port | notes |
|---|---|---|---|
| memos | `neosmemo/memos:0.29.1` | 5230 | journal front-end; `--allow-private-webhooks` |
| n8n | `n8nio/n8n:2.32.2` | 5678 | automation; reads config from container env |
| faster-whisper | `ghcr.io/speaches-ai/speaches:0.8.3-cpu` | 8010 | CPU; **no** Caddy vhost (internal only) |

Inference is **not** in this stack: the mini has no GPU, so n8n calls the rig's llama-swap
(`dolphin-venice-24b`, an uncensored-but-steerable coach). The rig's single 3090 Ti is shared
with Immich ML, so the coach is **best-effort** — see [GPU toggle](#gpu--coach-model-best-effort).

## First run

```bash
cd /opt/stacks/journaling
cp .env.example .env            # then fill MEMOS_API_TOKEN (see below); other keys have defaults
docker compose up -d            # brings up memos + n8n + faster-whisper
./scripts/healthcheck.sh        # curls all three + the rig coach endpoint
```

Caddy vhosts (`memos.tabaska.us`, `n8n.tabaska.us`) live in the mini's Caddy stack, not here;
faster-whisper is deliberately not exposed. On first visit to `https://n8n.tabaska.us` n8n asks
you to create an **owner account** (email + password — this is n8n's only login; it is not in the
vault, set your own). Memos credentials + PAT are at vault `journaling.memos.*`.

### Getting the Memos token + wiring the webhook (journal-02)

Memos 0.29 is a ConnectRPC API under `/api/v1` (not the old REST). The n8n workflow authenticates
to Memos with a **never-expiring Personal Access Token** (PAT). To mint one (already done — value
at vault `journaling.memos.api_token`, live in `.env` as `MEMOS_API_TOKEN`):

```bash
# 1) sign in for a short-lived access token
TOKEN=$(curl -s http://localhost:5230/api/v1/auth/signin \
  -d '{"passwordCredentials":{"username":"btabaska","password":"<vault journaling.memos.password>"},"neverExpire":true}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["accessToken"])')
# 2) mint a never-expiring PAT (the raw token is returned ONCE, at top level as .token)
curl -s -H "Authorization:Bearer $TOKEN" \
  http://localhost:5230/api/v1/users/btabaska/personalAccessTokens \
  -d '{"description":"n8n journal-analyze"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])'
# 3) register the webhook → the n8n container (private name; needs --allow-private-webhooks)
curl -s -H "Authorization:Bearer $PAT" http://localhost:5230/api/v1/users/btabaska/webhooks \
  -d '{"displayName":"n8n journal","url":"http://n8n:5678/webhook/journal"}'
```

`--allow-private-webhooks` (compose `command:` on the `memos` service) is what lets Memos POST to
the private container name `http://n8n:5678` — without it Memos silently drops private-IP targets.
One webhook receives **all** memo events; n8n filters. Registration closed to the public
(`instance/settings/GENERAL.disallowUserRegistration=true`).

### Enabling the analyze workflow (n8n 2.x gotcha)

The workflow source of truth is [`n8n/journal-analyze.workflow.json`](n8n/journal-analyze.workflow.json).
n8n **2.x** does not activate from a bare `active=1` flag — it needs a *published version* **and** a
restart:

```bash
docker exec n8n n8n import:workflow --input=/… /journal-analyze.workflow.json   # import
docker exec n8n n8n publish:workflow --id=<workflow-id>                          # publish
docker compose up -d n8n                                                         # restart to register
curl -s http://localhost:5678/webhook/journal   # armed iff it replies "…not registered for GET requests"
```

Two traps: (1) `import:workflow` **deactivates** the published version — re-`publish` after every
import; (2) CLI `unpublish`/re-import leaves a **stale `webhook_entity` row** that makes the next
workflow fail activation with "URL path … already taken" — clear it with n8n stopped
(`DELETE FROM webhook_entity WHERE workflowId='<old-id>'`, then start).

The workflow reads all its config from the **n8n container env** (`$env` in node expressions), so
swapping the coach model or Whisper endpoint is a one-line `.env` edit + `docker compose up -d n8n`:
`MEMOS_API_TOKEN`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_TEMP`, `WHISPER_BASE_URL`, `WHISPER_MODEL`.

## Testing end-to-end

```bash
# the verification runner's consumer-end probe (posts a #journal memo, asserts EXACTLY ONE
# reflection comment appears, then deletes the probe). Also runs in the daily 07:15 sweep.
python3 /opt/verification/bin/journaling-e2e.py         # -> E2E_OK (or E2E_SKIP_COACH_UNAVAILABLE)
```

Or by hand: create a `#journal` memo in the UI and watch a `🧭 **Reflection**` comment appear on
it within a few seconds (only if the coach model is loaded — best-effort).

## Native in-editor dictation (journal-08)

Memos 0.29.1 has a built-in **Settings → AI Integrations + Transcription** panel; it is wired to
the local stack, which lights up the **Transcribe** button on the editor's audio recorder (record →
tap transcribe → the spoken text lands in the entry). This is server-side — the browser sends the
audio to Memos (`/api/v1/ai:transcribe`) and *Memos* calls the provider — so the provider endpoint
is the **container** name `http://faster-whisper:8000/v1`, exactly like n8n's branch. It is a
separate path from the `journal-04` n8n branch (which transcribes audio *attachments* after save);
both use the same Speaches container and model (`Systran/faster-whisper-small`).

A second provider, `rig-litellm` (`http://192.168.10.12:4000/v1`, least-priv virtual key scoped
`chat`+`utility`, canonical vault `ai_stack.litellm_memos_key`), is pre-wired for future Memos AI
features — nothing in 0.29.1 consumes it yet.

The whole panel lives **only in the Memos sqlite** (`instance/settings/AI` — no compose file owns
it), so a DB wipe/restore loses it silently. Re-seed with:

```bash
cd /opt/stacks/journaling && MEMOS_LLM_KEY=<vault ai_stack.litellm_memos_key> ./scripts/seed-memos-ai.sh
```

The daily `journaling-memos-native-transcribe` check drift-gates the setting and then pushes the
bundled probe WAV through Memos' own `ai:transcribe` (the real button path).

## Agent access via MCP (journal-09)

Memos ships a **built-in MCP server** at `/mcp` (since 0.27), and it is wired into the local AI
stack so agents can work with the journal conversationally:

- **OWUI chat** (rig): native MCP connection `memos`, filtered to **`search_memos` + `create_memo`**
  only ("what did I write about X?", "save a memo that…") — destructive tools stay out of chat, and
  the OWUI visible-tool budget sits at exactly 40/40. Enable it per-chat via the tools picker.
- **opencode** (rig + Mac): the full 19-tool set via a remote MCP entry (`{env:MEMOS_MCP_TOKEN}`).

Auth is a **dedicated PAT** (vault `journaling.memos.mcp_token` — separate from n8n's, revocable
alone). Canonical wiring is in the **local-ai-tooling repo**: `scripts/seed-owui-tool-servers.sh`
(injects the PAT at run time; re-run after an OWUI volume wipe) + `clients/opencode.json`. The n8n
reflection loop does **not** use MCP — it stays webhook + REST by design. Guarded by the fast
`journaling-memos-mcp` check (real MCP handshake + OWUI connection drift gate).

## Templates

- [`templates/daily.md`](templates/daily.md) — `#journal`.
- [`templates/gamelog.md`](templates/gamelog.md) — `#gamelog #journal` (flows through the same
  analysis; IGDB metadata enrichment (`journal-07`) is LIVE — a 🎮 comment is added from the
  `**Game:**` line, alongside the 🧭 reflection).

## Backup & export

- **Backup (complete, automatic):** restic backs up the whole stack dir nightly to Backblaze B2
  (`BACKUP_PATHS` includes `/opt/stacks`; `restic-backup.timer` on the mini, ~01:40). That captures
  **everything** — Memos sqlite + uploads (`memos/`), the n8n workflows **and encryption key**
  (`n8n/`), and the Whisper model cache (`whisper-cache/`). Restore a single path with, e.g.:
  ```bash
  sudo bash -c '. /etc/restic/env; restic restore latest --target /restore --include /opt/stacks/journaling'
  ```
  The n8n **encryption key** (`n8n/config`) is required to decrypt saved credentials — it is in the
  backup but never in this repo (see `.gitignore`); losing it means re-entering credentials.
- **Export (portable JSON):** [`scripts/export-journal.sh`](scripts/export-journal.sh) dumps every
  entry **and its reflection comments** to JSON via the Memos API (for migrating to another Memos or
  reading offline). The list API returns entries only, so the script fetches each entry's comments
  too:
  ```bash
  cd /opt/stacks/journaling && ./scripts/export-journal.sh   # -> journal-export-YYYY-MM-DD.json
  ```

## Monitoring

- **Verification runner** (`foss-setup/verification/checks.d/journaling.yaml`, on the mini runner):
  readiness probes for all three services + the rig coach dependency + wiring invariants, the
  consumer-end **`journaling-loop-e2e`** (one memo → exactly one comment), and
  **`journaling-memos-native-transcribe`** (the native Transcribe-button path, `journal-08`).
  Alerts → ntfy topic `verification`.
- **Uptime-Kuma** (mini `:3001`): `Mini Memos` + `Mini n8n` liveness tiles (health endpoints),
  seeded by `foss-setup/scripts/uptime-kuma/seed-monitors.sh`, alerting to ntfy.
- **Homepage** `Journaling` group: two tiles for Memos + n8n.

## Troubleshooting

**No reflection comment appears.** Most often the coach model isn't loaded — it's best-effort (see
below). Confirm it's reachable: `curl -s http://192.168.10.12:9292/v1/models | grep dolphin-venice-24b`,
and that the workflow is armed: `curl -s http://localhost:5678/webhook/journal` must say
"…not registered for GET requests". The entry is always saved regardless.

**Duplicate/looping reflections.** The loop guard (Guard Code node) proceeds only on
`memos.memo.created` carrying `#journal`, and drops `memos.memo.comment.created` **and** any memo
whose content starts with the `🧭` reflection sentinel — because writing a comment fires **two**
webhook events, both carrying the *comment* memo. If reflections loop, the guard regressed; re-check
`n8n/journal-analyze.workflow.json`.

**Memos entries create but n8n never fires.** The webhook must still point at
`http://n8n:5678/webhook/journal` (`curl -s -H "Authorization:Bearer $MEMOS_API_TOKEN"
http://localhost:5230/api/v1/users/btabaska/webhooks`), and Memos must run with
`--allow-private-webhooks` (`docker inspect memos --format '{{json .Config.Cmd}}'`).

<a name="gpu--coach-model-best-effort"></a>**GPU / coach model (best-effort).** The coach
(`dolphin-venice-24b`, ~17 GB) shares the rig's single 24 GB 3090 Ti with Immich ML. When the card
is tight the model fails to load — llama-swap returns 500 "upstream command exited prematurely" — and
n8n retries 3× then posts nothing (the entry is still saved). This is expected, not a bug. Swap to a
lighter/loadable model for a while by editing `.env` (`LLM_MODEL=fast-3b` to prove the loop, or
`deckard-heretic` for the bigger creative alt) + `docker compose up -d n8n`. faster-whisper is CPU
(no GPU block) for the same reason; a commented GPU variant is in `compose.yaml` if a GPU host ever
runs it.

**Voice notes not transcribed.** `journaling-whisper-ready` only proves `/health`; the model loads
lazily on first real call. Test a real transcription:
`curl -s -m 90 -X POST http://localhost:8010/v1/audio/transcriptions -F file=@some.wav -F
model=Systran/faster-whisper-small`. From n8n the endpoint is the **container** port
`http://faster-whisper:8000/v1` (host `:8010` is only a publish mapping). Whisper failing never
blocks a normal entry — both HTTP nodes are continue-on-error and the merge falls back to text.

**Open WebUI coach/save button gone.** The `Journaling Coach` preset + `Save to Journal` action live
only in the rig OWUI database (no compose owns them) — an OWUI volume wipe erases them. Reinstall from
`openwebui/` via the OWUI admin API (see `wiki/docs/services/journaling.md`); the drift-guard checks
`journaling-owui-*` catch this.

**General.** `./scripts/healthcheck.sh` on the mini; `docker compose logs --tail 50 <service>`; the
n8n + whisper bind-mount dirs must stay owned by uid 1000.
