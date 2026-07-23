# Self-hosted AI journaling stack — build plan (source of truth)

**Source:** user request 2026-07-22 (paste of an 8-step "AI journaling stack" implementation
prompt). This doc is the canonical spec for tasks **`journal-01`…`journal-07`**. A cold
`/build-next` session should read this in full before building a `journal-*` task.

The original prompt assumed a plain Ollama with a capable 27B model. **That is not how the rig
works** — the decisions below reconcile the prompt with the real fleet. Build to *this* doc, not
to the prompt's literal `<<PLACEHOLDER>>` defaults.

## Goal

A fully **local, LAN-only** AI journaling stack: a journaling front-end (Memos), an automation
layer (n8n) that reacts to each new entry and writes back a short, gentle reflection as a
**comment** (never editing the entry), a local speech-to-text endpoint (faster-whisper) for the
optional server-side dictation path, and Open WebUI tooling for free-form coaching conversations
that can be saved back into the journal. **No external/cloud calls, no telemetry.**

## Locked decisions (from the 2026-07-22 grounding + user answers)

| decision | value | why |
|---|---|---|
| **Tone / feel** | **Gentle nudge** | Mostly stays quiet; light touch, at most one short question. Lowest-pressure so it doesn't get abandoned. Drives the coaching system prompt. |
| **Where it runs** | **mini** (`/opt/stacks/journaling/`) | The general Docker workhorse (dockge, restic, Forgejo-mirrored). Inference stays on the rig; the mini reaches it over LAN. Keeps the rig focused on GPU work. |
| **Coach model** | **`dolphin-venice-24b`** via rig **llama-swap** `http://192.168.10.12:9292/v1/chat/completions`, temp ≈ **0.35** | Genuinely uncensored (won't refuse/moralize on raw entries) *and* fully steerable by the system prompt — exactly what a gentle-nudge persona + strict-JSON contract needs. Low temp for stable JSON. `deckard-heretic` (31B) is the bigger/creative alt but VRAM-tight (<1 GB headroom, OOMs during gaming) — offer as a one-line `.env` swap only. |
| **Inference endpoint** | llama-swap `:9292` (OpenAI-compatible), **not** raw Ollama `:11434` | The `:11434` Ollama only holds small models (llama3.2:3b, nomic-embed-text). Capable models live behind llama-swap; the creative/RP models are **not** registered in LiteLLM `:4000`, so hit llama-swap directly. LAN-local, satisfies "local only". |
| **Repo integration** | **Full homelab wiring** | Proper stack mirrored to `foss-setup/`, Homepage tiles, consumer-end verification checks, coverage manifest, wiki page, tracker tasks. No drift. |
| **Network / privacy** | LAN + tailnet only, no public exposure, Memos auth ON, faster-whisper internal-only | Whole-fleet ethos; journaling is private. |
| **Reminders** | none (gentle nudge = templates + on-demand, no nagging) | Can add a scheduled prompt later if wanted. |
| **Crisis handling** | keep the crisis clause in the system prompt (brief, caring, encourage reaching out; no medical advice) | The uncensored model won't refuse heavy entries — the clause handles safety in tone, not refusal. |
| **Dictation** | primary = client-side (text lands in Memos); server-side Whisper branch shipped but secondary | Matches the prompt. |

## Pinned images (no `:latest`; verify the tag still resolves at build time)

| service | image | port (host) | notes |
|---|---|---|---|
| Memos | `neosmemo/memos:0.29.1` | `5230` | 0.30 is RC-only. Run with private-webhooks allowed (see risk 1). |
| n8n | `n8nio/n8n:2.32.2` | `5678` | current stable (exclude nightly/next/beta). |
| faster-whisper | `ghcr.io/speaches-ai/speaches:0.8.3-cpu` | **`8010`** | Speaches = maintained successor to `fedirz/faster-whisper-server`. **CPU** by default (`:8000`/`:8080` already taken on the mini). Keep a commented GPU block (NVIDIA runtime + CUDA image) but note GPU competes with the rig's 24 GB single 3090 Ti — leave CPU. |

Digest-pin new images at build (fix-38 / supply-chain posture) and note the pin's provenance.

## Architecture / data flow

```
 you write / dictate ──► Memos (#journal)
                            │  webhook: memo.created  (--allow-private-webhooks)
                            ▼
                          n8n  "journal-analyze"
                            ├─ filter: only memo.created; SKIP comment events + already-analyzed
                            ├─ (optional) audio resource? ─► faster-whisper /v1/audio/transcriptions ─► merge transcript
                            ├─ LLM: POST rig :9292 /v1/chat/completions  model=dolphin-venice-24b temp≈0.35  (strict JSON)
                            └─ write-back: create a COMMENT on the source memo (never edit the body)
 Open WebUI "Journaling Coach" preset ─┐
 Open WebUI "Save to Journal" fn ──────┴─► POST Memos /api/v1/memos as #journal ─► (re-enters the loop, intentionally)
```

**Loop prevention (critical):** write results as a *comment*, not a body edit; the workflow must
skip comment-created events and skip any memo already carrying an analysis comment / `#analyzed`
marker. It must never analyze its own output.

## Coaching system prompt (gentle-nudge variant — bake into the n8n LLM node)

> You are a quiet, warm journaling companion. You receive ONE journal entry. Respond ONLY with
> valid JSON in exactly this schema:
> ```json
> {
>   "sentiment": "<very negative|negative|neutral|positive|very positive>",
>   "mood_score": <integer 1-10>,
>   "emotions": ["<up to 4>"],
>   "themes": ["<up to 4>"],
>   "summary": "<one-sentence reflection of what this entry is about>",
>   "coaching": "<1-2 sentences, gentle and low-pressure. Reflect back one specific thing. At MOST one soft, open-ended question — and only if it genuinely helps. No advice, no clichés, no cheerleading. It is fine to simply witness.>"
> }
> ```
> Be honest and specific, never saccharine. Stay light — you are a nudge, not a coach. If the
> entry suggests crisis or self-harm risk, set `coaching` to gently, briefly encourage reaching
> out to a trusted person or professional. Never give medical advice.

n8n formats the JSON into a Markdown comment:
```
🧭 **Reflection** · mood <mood_score>/10 · <sentiment>
_Emotions:_ <emotions>  ·  _Themes:_ <themes>

<coaching>
```

## Journaling templates (repo `templates/`, documented in the README)

- `daily.md` — tag `#journal`.
- `gamelog.md` — tags `#gamelog #journal` (Backloggd replacement; flows through the same analysis
  because it also carries `#journal`). TODO note: IGDB metadata enrichment is Phase 2 (`journal-07`).

## The 8 prompt-steps → tracker tasks

The prompt's build order is covered by `journal-01…06` (two steps fold into an adjacent task so
each task is an independently shippable, consumer-verifiable `/build-next` session). Phase-2 IGDB
is `journal-07` (deferred).

| prompt step | task | notes |
|---|---|---|
| 1 scaffold + bring up + reachability | **journal-01** | + healthcheck.sh (step 2 folds in here — it's the bring-up's own verification), Caddy vhosts, Homepage tiles, coverage manifest. |
| 2 run healthcheck | *(folded into journal-01)* | not its own session — it's journal-01's acceptance. |
| 3 Memos token + webhook → n8n, confirm events | **journal-02** | mints Memos account + API token; `--allow-private-webhooks`; n8n logs raw payload. |
| 4 build journal-analyze workflow + loop guard | **journal-03** | filter → (opt transcribe) → LLM → format → comment; tolerant JSON parse; loop guard. |
| 5 test end-to-end (#journal, then #gamelog) | *(folded into journal-03)* | `/build-next` requires end-to-end consumer verification anyway — you can't ship the workflow without proving one memo → exactly one comment, no re-trigger. Ships `templates/`. |
| 6 faster-whisper endpoint + transcription branch | **journal-04** | secondary/optional path; text path must stay unaffected. |
| 7 Open WebUI coach preset + Save-to-Journal fn | **journal-05** | on rig open-webui; saved convo → Memos `#journal` → analyzed. |
| 8 README + backup/export + full monitoring/wiki closeout | **journal-06** | README (token walkthrough, `--allow-private-webhooks`, loop guard, GPU toggle, backup/export), wiki page, end-to-end verification check, Uptime-Kuma, confirm 100% coverage. |
| Appendix Phase-2 IGDB enrichment | **journal-07** (deferred) | Twitch dev-app creds (ai-vault); graceful-degrade; loop-safe comment; do NOT build until user opts in. |

## Two build-time risks to validate (do not assume)

1. **Memos 0.29 webhook + comment API + `--allow-private-webhooks`.** Confirm the webhook activity
   payload shape and the memo-comment endpoint on *this* pinned version (`journal-02` logs the raw
   payload). If the private-webhook flag isn't honored, route the webhook via the Caddy hostname
   (`n8n.tabaska.us`) so the target isn't a private-IP literal.
2. **dolphin-venice JSON reliability at low temp.** Add a tolerant JSON-extract/repair step in n8n
   so a chatty or fenced response never breaks the loop. Also: llama-swap swaps the model in on
   first call (~17 GB, a few seconds) and a "gaming force-unload" hook can evict it — the analysis
   is best-effort; the entry is saved regardless. n8n LLM node needs a generous timeout + retry.

## Deliverable layout (mirrored: live `/opt/stacks/journaling/` ↔ repo `configs/docker-stack/stacks/journaling/`)

```
journaling/
├── compose.yaml                # memos + n8n + faster-whisper (CPU default; GPU block commented)
├── .env.example                # RIG_IP, LLM URL+MODEL, ports, TZ, token key NAMES only
├── n8n/journal-analyze.workflow.json
├── openwebui/save_to_journal_function.py
├── openwebui/journaling-coach-preset.md
├── templates/{daily.md,gamelog.md}
└── scripts/healthcheck.sh      # curls Memos, n8n, faster-whisper, rig llama-swap
```
Secrets (Memos API token, OWUI admin if needed) → vault `journaling.*`, **merge never blind-assign**;
`.env.example` carries key names only. README lives in the stack dir; wiki prose via
`service-enrichment.yaml`.

## Risk 1 — VALIDATED on memos 0.29.1 (journal-02, 2026-07-22)

journal-02 created the host account, minted the token, wired the webhook, and captured live
payloads. These are **facts from this pinned build** — journal-03 builds the filter/loop-guard
against them, do not re-derive.

**Memos 0.29 API is ConnectRPC (not the old REST), all under `/api/v1`:**
- Auth: `POST /api/v1/auth/signin` body `{"passwordCredentials":{"username","password"},"neverExpire":true}`
  → returns `{"user":{…},"accessToken":"<JWT, ~15min>"}` **in the body** (no cookie for the access
  token; a `memos_refresh` HttpOnly cookie is set via a `Grpc-Metadata-Set-Cookie` header). Use
  `accessToken` as `Authorization: Bearer …`.
- **Personal Access Token** (the long-lived n8n credential): `POST /api/v1/users/{username}/personalAccessTokens`
  body `{"description":"…"}` (flat). The raw token is returned **only once**, at the **top level** as
  `.token` (`memos_pat_<32>`, opaque, sha256-hashed in `user_setting.PERSONAL_ACCESS_TOKENS`,
  `expiresAt:null` = never expires). It is **revocable** by DELETE (verified: deleted token → 401
  on auth-required endpoints). Note `GET /api/v1/users/{username}` is **public** (200 with any/no
  token) — never use it as an auth probe; list PATs instead.
- **Webhook**: `POST /api/v1/users/{username}/webhooks` body `{"displayName","url"}` (flat; **no**
  `webhook:` wrapper, **no** activityType filter — one webhook receives ALL memo events, n8n filters).
- **Comment**: `POST /api/v1/memos/{name}/comments` body `{"content","visibility"}`. A comment **is a
  memo** linked by a COMMENT relation to the parent.
- Resource name = `users/{username}` and `memos/{uid}` (not numeric ids).

**Webhook delivery** works via `--allow-private-webhooks` (compose `command: ["--allow-private-webhooks"]`,
passed through memos' `entrypoint.sh` `exec "$@"`) → target is the **container name**
`http://n8n:5678/webhook/journal` (fully local; no DNS/Caddy/TLS hop). Verified from inside the memos
container and end-to-end via a real memo.

**Captured payload shapes** (n8n Webhook node `body`) — note these differ from the REST API JSON:
fields are **snake_case**, timestamps are `{"seconds":<unix>}` (not RFC3339), enums are **ints**
(`state:1`=NORMAL, `visibility:1`=PRIVATE), and `tags` is a parsed array of hashtags.

```jsonc
// memos.memo.created  (a top-level entry)
{ "activityType": "memos.memo.created", "creator": "users/btabaska",
  "memo": { "name":"memos/XXXX", "creator":"users/btabaska", "content":"… #journal",
            "tags":["journal"], "state":1, "visibility":1, "snippet":"…",
            "create_time":{"seconds":1784774650}, "update_time":{…}, "property":{} } }
```

**⚠ Loop guard (critical for journal-03):** creating a **comment** fires **TWO** webhook events —
first `memos.memo.created`, then `memos.memo.comment.created` — and **both carry the *comment* memo**
in `.memo` (the parent is not in the payload). So filtering on `activityType == memos.memo.created`
alone is **not enough**: the reflection comment n8n writes back would re-trigger analysis → infinite
loop. The workflow must, on `memos.memo.created`, **skip memos that are comments** (fetch the memo /
check for a parent relation, or skip any memo whose content carries the analysis marker /
`#analyzed`) and **ignore `memos.memo.comment.created` entirely**.

**Security note:** memos ships with public user registration **on** — journal-02 set
`instance/settings/GENERAL.disallowUserRegistration=true` (PATCH `/api/v1/instance/settings/GENERAL`;
"workspace" was renamed **InstanceService** in 0.29). Verified: unauth `POST /api/v1/users` → 403.

Secrets: `journaling.memos.{username,password,api_token,webhook_url}` in the vault; the token is also
in the live stack `.env` as `MEMOS_API_TOKEN` (600) for n8n to consume in journal-03.
