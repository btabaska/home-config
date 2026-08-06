# Agent memory layer (opencode MEMORY.md + OWUI native Memory)

Runbook for the `agent-memory-plugin` verification check and the fleet's two
agent-memory surfaces (lai-18, local-ai buildout):

1. a **DIY markdown memory plugin for opencode** (the terminal coding agent), and
2. **Open WebUI's native Memory** (the 8 built-in memory tools) for the chat UI.

opencode has no built-in memory (AGENTS.md is static, `/init`-only) and its session
storage moved to an internal SQLite `opencode.db` (the legacy JSON `storage/` tree is
gone), so the plugin reads transcripts through the **plugin SDK client**, never the DB.

## 1. The opencode memory plugin

- **File (canonical):** `local-ai-tooling` repo `agentic/opencode/plugins/memory.ts`
  (dual-remoted — push **both** GitHub `origin` + Forgejo). Deployed to
  `~/.config/opencode/plugins/memory.ts` on **both the Mac and the rig** (auto-loaded
  at startup; no `plugin`-array registration needed, same as `local-llm.ts`).
- **Summarizer model:** LiteLLM **`utility`** (Llama-3.2-3B). Deliberately the smallest
  model and **one call at a time** (global single-flight) — a memory plugin must never
  fan out background/parallel LLM calls on the single 24 GB card (see the GPU-contention
  policy). The 3B call is a plain `/v1/chat/completions`, not an agent turn, so it is
  unaffected by opencode's tool-calling.
- **Triggers:**
  - `session.idle` — **awaited** (in `opencode run` the process exits right after idle,
    so a fire-and-forget summary would be killed mid-flight; awaiting is safe because the
    call is debounced + single-flight + hard-timeout-bounded).
  - `experimental.session.compacting` — best-effort (fire-and-forget) capture right before
    the transcript is pruned.
- **What it writes:** the model is prompted to extract only durable facts/decisions/
  gotchas (NOT chit-chat) as a flat bullet list, or `NONE`. Output is **secret-scrubbed**
  (JWTs, `sk-`/`ghp-`/… keys, `Bearer` tokens, long hex, `password=`/`token=` assignments
  → `[redacted]`) and **de-duplicated** against the existing file (normalized bullet match)
  before a dated `## <YYYY-MM-DD HH:MM> UTC (idle|compacting)` block is appended.
- **Guards:** skip empty/trivial sessions (< 400 chars transcript, < 2 new messages), an
  **8-minute per-session debounce** (idle fires constantly), single-flight, 60 s HTTP
  timeout, and every hook is wrapped so it can never throw into an agent turn.
- **Read-back (closes the loop):** `experimental.chat.system.transform` injects the
  project's MEMORY.md back into the system prompt each turn (capped ~6 KB, most-recent
  tail). Proven end-to-end: a fresh session whose own transcript never stated a fact
  recalled it from injected memory.

### Where MEMORY.md lives / its format

- **Location:** `${OPENCODE_MEMORY_DIR:-~/.local/share/opencode/memory}/<project-slug>.md`,
  one file **per project** (`<basename>-<hash-of-full-path>`). It lives **outside any git
  repo on purpose** — a runtime-written file inside `local-ai-tooling` would perpetually
  dirty that checkout and trip `ai-tooling-clean-pushed`.
- **Format:** a title line, then append-only dated sections, each a flat `- ` bullet list.

```
# Project memory — <project>

## 2026-08-06 19:41 UTC (idle)
- billing-worker listens on TCP port 8422
- deploys happen only on Tuesdays
```

### The check

`agent-memory-plugin` (`verification/checks.d/local-ai.yaml`, `host: rig`, warn,
fast tier) is **deterministic and GPU-safe — it makes NO model call.** On the rig it
asserts: (1) `memory.ts` is present, (2) it still carries its core wiring
(`session.idle` + `experimental.session.compacting` triggers + the `chat/completions`
summarizer call — a gutted plugin fails here), (3) it is syntactically valid
(`node --experimental-strip-types --check`), and (4) at least one project MEMORY.md
exists with a well-formed dated `(idle|compacting)` section + `- ` bullets (which only
appears once the write path has actually run). Expect `MEM_OK …`.

Run it in isolation from the mini (audit-safe):

```bash
VERIFICATION_STATE_DIR=$(mktemp -d) /opt/verification/bin/run-checks.sh --no-notify --host local-ai
```

**If `MEM_NO_PLUGIN`:** re-deploy the plugin — `scp agentic/opencode/plugins/memory.ts
rig:~/.config/opencode/plugins/memory.ts`. **If `MEM_PLUGIN_SYNTAX_BAD`:** a bad edit —
`node --experimental-strip-types --check` it locally before deploying. **If `MEM_NO_FILE`:**
no opencode session has produced durable memory on the rig yet — run one (`opencode run`
in any project, establish a fact) or check `LITELLM_API_KEY` is exported in the rig shell.

## 2. Open WebUI native Memory — status & finding (lai-18)

OWUI **0.10.2** ships the graduated Memory feature: 8 built-in tools
(`add_memory`, `update_memory`, `replace_memory_content`, `delete_memory`,
`search_memories`, `list_memories`, `list_memory_paths`, `read_memory_path`).

- **Enabled** and left on: live DB config `memories.enable=True` and
  `memories.system_context.enable=True` (saved memories are injected into the system
  prompt); Native function-calling is on for `coder`/`code`/`coder-strong`/`chat`.
  `memories.background_review.enable` is deliberately **False** — the background reviewer
  fires unattended LLM calls, which the single-GPU curation rule forbids.
- **Gating (source-verified):** the 8 tools attach only when a request carries a UI
  `session_id` (`use_builtin_tools` in `utils/middleware.py`) **and** the request sets
  `features.memory=true` (the per-user Memory toggle). Pure REST-API callers get **no**
  builtin tools by design — the code comment is explicit: *"API callers don't expect
  hidden tools."* A naive API call therefore makes the model **hallucinate**
  `add_memory(...)` as plain text and falsely claim it saved — not a real invocation.
- **Reliability finding (the flagged unknown): local models DO reliably invoke the memory
  tools.** With the tools actually attached, three native-FC local models each emitted a
  **well-formed native `add_memory` tool_call** with correct arguments:
  - `coder` (Qwen3.6-35B-A3B) → `{"content":"Canary code: ZEPHYR-8422","type":"user"}`
  - `chat` (Gemma-4-31B-QAT) → `{"content":"The user's canary code is ZEPHYR-8422.","type":"user"}`
  - `coder-strong` (Qwen3.6-27B) → `{"content":"…","path":"canary","type":"user"}` (used the optional `path`)
- **Caveat:** the full execute-and-persist loop runs only in the UI/WebSocket path;
  OWUI's synchronous API response returns the tool_call without executing it, so
  head-less REST cannot assert end-to-end persistence — only that the model invokes the
  tool. In the actual chat UI (Memory toggle on) the loop completes and the memory persists.

**Bottom line:** memory works in the OWUI chat UI with local models; there is no reliable
head-less API path to drive it, so there is intentionally no live-model OWUI memory check.
