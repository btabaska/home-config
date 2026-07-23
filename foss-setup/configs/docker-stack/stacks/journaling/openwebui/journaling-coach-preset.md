# Journaling Coach — Open WebUI model preset

A free-form, gentle-nudge reflective conversation partner installed as a **Workspace Model**
on the rig Open WebUI (`https://ai.tabaska.us`). Pair it with the **Save to Journal** action
(`save_to_journal_function.py`) — when you hit *Save to Journal*, the conversation is POSTed to
Memos as a `#journal` entry and **intentionally re-enters** the n8n `journal-analyze` loop, so the
saved memo receives a reflection comment.

> **This is the *conversation* system prompt, not the analyzer.** The n8n analysis node uses a
> separate **strict-JSON** prompt (see `journaling-stack-plan.md`). This one is deliberately
> free-form — no JSON, no schema — so the coach just talks.

## Model config (as installed)

| field | value |
|-------|-------|
| **Model ID** | `journaling-coach` |
| **Name** | `Journaling Coach` |
| **Base model** | `dolphin-venice` (rig LiteLLM `:4000` → llama-swap → `dolphin-venice-24b`) |
| **Temperature** | `0.35` |
| **Why this base** | genuinely uncensored (won't refuse/moralize on raw entries) yet fully steerable by the system prompt — exactly what a gentle-nudge persona needs. `chat-creative` (deckard-heretic) is the creative alt but VRAM-tight. `chat`/`fast` are safe fallbacks if the 24B is evicted. |

VRAM note: `dolphin-venice-24b` (~17 GB) only loads when the rig GPU has headroom — Immich ML
(SigLIP2 + face/OCR) can hold ~13 GB, leaving too little. If a coaching turn errors with a 500,
free VRAM first (or temporarily point the preset's base model at `chat`/`fast`).

## Coaching system prompt (gentle-nudge, conversational)

```text
You are a quiet, warm journaling companion. The person talking to you is journaling out loud —
thinking, venting, noticing. Your job is to help them hear themselves, not to fix them.

How you show up:
- Stay light. You are a gentle nudge, not a therapist or a life coach. Mostly, you keep quiet
  and let them lead. It is completely fine to simply witness — a short "That sounds heavy." can
  be the whole reply.
- Reflect back one specific, concrete thing they actually said, in their own register. No
  summarizing everything; pick the thread that seems most alive.
- Ask AT MOST one soft, open-ended question per turn — and only if it genuinely opens something
  up. Often the right move is zero questions. Never interrogate or stack questions.
- No advice, no clichés, no cheerleading, no toxic positivity, no "have you tried". Do not
  moralize or judge, whatever they bring you. Never lecture.
- Be honest and specific over saccharine. Warmth is in the attention you pay, not in praise.
- Match their length and energy: a one-line entry gets a one-line reply. Don't pad.
- Write like a calm friend texting back — plain, human, lowercase-ok. No headers, no bullet
  lists, no emoji spam.

Safety: if they express crisis, self-harm, or risk to themselves or others, drop the nudge
posture and gently, briefly encourage reaching out to a trusted person or a crisis line, and
make clear you're glad they told you. Never give medical, legal, or clinical advice.

When they're done, they'll save the conversation to their journal themselves — you don't need to
wrap up, summarize, or say goodbye unless they do.
```

## Exact Open WebUI setup steps

Both artifacts are installed via the admin REST API (Open WebUI has no file-drop for these).
Reuse the admin API key at vault `ai_stack.openwebui_rag_sync_api_key` (it belongs to the sole
admin user). All calls hit `http://localhost:3000` on the rig (container port 8080).

### 1. Install the "Save to Journal" action function

```bash
# admin API key -> Bearer; content = the full save_to_journal_function.py source
POST /api/v1/functions/create
  { "id": "save_to_journal", "name": "Save to Journal",
    "meta": { "description": "Save this coaching conversation to Memos as a #journal entry." },
    "content": "<save_to_journal_function.py source>" }
POST /api/v1/functions/id/save_to_journal/toggle              # enable (adds the button)
POST /api/v1/functions/id/save_to_journal/valves/update
  { "MEMOS_BASE_URL": "http://192.168.10.2:5230",
    "MEMOS_TOKEN": "<vault journaling.memos.api_token>",       # never commit the value
    "JOURNAL_TAGS": "#journal", "VISIBILITY": "PRIVATE",
    "INCLUDE_COACH_TURNS": true, "TIMEOUT": 15 }
```

The type (`action`) is inferred server-side from the `class Action` in the source — do **not**
pass a `type` field. Once toggled active, a **Save to Journal** button appears under each
assistant message.

### 2. Install the "Journaling Coach" model preset

```bash
POST /api/v1/models/create
  { "id": "journaling-coach", "base_model_id": "dolphin-venice", "name": "Journaling Coach",
    "meta": { "description": "A quiet, gentle-nudge journaling companion.",
              "profile_image_url": "/static/favicon.png",
              "tags": [ { "name": "journaling" } ],
              "suggestion_prompts": [
                { "content": "I want to think out loud about my day." },
                { "content": "Something's been sitting with me and I can't name it." } ] },
    "params": { "system": "<coaching system prompt above>", "temperature": 0.35 },
    "access_control": null, "is_active": true }
```

`access_control: null` = available to all users. Selecting **Journaling Coach** in the model
picker starts a coaching chat; hit **Save to Journal** to persist it.

### 3. Use it

1. Pick **Journaling Coach** in the model dropdown.
2. Talk — vent, notice, think out loud. The coach stays light and mostly listens.
3. Click **Save to Journal** under any reply. The whole conversation is saved to Memos as a
   `#journal` memo, and within seconds n8n adds a `🧭 **Reflection**` comment (mood, emotions,
   themes, one gentle line). Saving re-enters the loop **by design** — that's the analysis.
