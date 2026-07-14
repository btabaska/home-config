# Local-AI build plan

> The design for a first-class, local-first AI coding + home-ops/Q&A stack on the rig's single RTX 3090 Ti (24 GB), built on the existing Ollama/LiteLLM/Open WebUI base.

_Source: `foss-setup/docs/local-ai-build-plan.md` · migrated + validated 2026-07-14._

**Status:** plan drafted from deep research (2026-07-13); this is the tracked design for the `ai-01` initiative. The **shared base infra is already live on the rig** (Ollama + LiteLLM + Open WebUI + mcpo — see [Live state](#live-state-validation-2026-07-14)). The two build pillars below (opencode agentic coding, ollmcp ops agent, RAG) are **planned, not yet deployed** — treat every "Plan Pass" step as aspirational until built.
**Origin:** roadmap prune (#17) — operator chose to keep + expand `ai-01` into its own workstream.
**Constraints locked with operator 2026-07-13:** a single RTX 3090 Ti **24 GB is a hard ceiling** (no GPU spend); runtime chosen **on merit**; build a **shared base infra** then two separate plan passes (coding + ops/Q&A).

> The AI stack runs **entirely on the rig** (`192.168.10.12`, 24/7) and its compose lives in a **separate repo** (`local-ai-tooling`), not in `foss-setup/`. It has **no fallback** — rig down = the whole AI surface down (an accepted soft SPOF). "LiteLLM on the mini" is a phantom that was never deployed.

---

## TL;DR — the honest verdict

A local-only build on this 24 GB card can serve **~80% of day-to-day coding** (single-file edits, bug fixes, test generation, boilerplate, refactors) and **reliable tool-using ops/Q&A agents** — but it **cannot reach frontier parity**. The 2026 leaderboard-topping coders are 700 B–1 T MoE models needing 200 GB+ VRAM; self-hostable-in-24 GB models top out ~68–77% SWE-bench Verified vs 80–95% for frontier cloud — a **17–27-point gap**, concentrated in post-training-cutoff API knowledge, 100 k+-token multi-file reasoning, and debugging accuracy. Set expectations accordingly: **local is the daily driver for bounded work; it is not a Claude-Code replacement for the hardest multi-file/cross-repo tasks.** [high confidence — 3-0 verified]

**Runtime call:** stay in the **llama.cpp / Ollama (GGUF)** ecosystem already running — for a *single user sharing the GPU with gaming* it matches vLLM's token rate and, unlike vLLM, doesn't pre-grab ~90% of VRAM at startup (which would starve game streaming). vLLM's edge is real but only appears under concurrent multi-user load. [high confidence — 3-0 on single-concurrency parity]

**The decisive variable is model choice, not size:** opencode's own docs warn "only a few models are good at BOTH generating code and tool calling" — the core requirement for agentic use. Pick for that, then fit it to VRAM. [high — 3-0]

---

## Verified findings (what survived 3-vote adversarial verification)

| # | Finding | Conf. | Sources |
|---|---|---|---|
| 1 | **No frontier parity on 24 GB.** Top 2026 coders (GLM-5.2 744B, Kimi K2.7 ~1T, DeepSeek V4, Qwen3-Coder 480B) need 200 GB+. Local 24 GB tops ~68–77% SWE-bench vs 80–95% cloud. Lags on new-API knowledge, long-context multi-file, debugging — but handles ~80% of daily work. | high | pactentia, promptquorum, insiderllm |
| 2 | **VRAM tiers (this card):** 24B-class Q4_K_M (Mistral Small 24B, Codestral 22B) ≈ 23.6 GB / ~36 K ctx = balanced sweet spot; **27B dense Q4 ≈ 17 GB weights** (comfortable, room for big KV) — best fit; 32B dense Q4 ≈ 23.4 GB but only ~12 K ctx / ~22 t/s; **30–35B-A3B MoE Q4 ≈ 22–24 GB**, faster (~35 t/s @ 32 K) but no room to co-locate a 2nd model. | med | hardware-corner, insiderllm |
| 3 | **Runtime: llama.cpp/Ollama over vLLM here.** Single-concurrency token rates comparable (~1.1×); vLLM only wins under concurrency (≈6× @ 50 users). vLLM pre-allocates ~90% VRAM at startup → starves gaming; llama.cpp/Ollama load/unload and don't pre-grab. | high | Red Hat Developer (2026-06), insiderllm |
| 4 | **opencode + local:** supports 75+ providers incl. local via OpenAI-compatible `baseURL`, but **every "works well" recommended model is frontier/cloud** — no small local model is endorsed. Its docs stress few models do code+tools both well. | high | opencode.ai/docs/models (primary) |
| 5 | **Safe LAN ops agent: `ollmcp` (mcp-client-for-ollama)** — agentic tool-calling loop (configurable loop limit, default 7) with **human-in-the-loop approval** (per-call / session / abort) over MCP tools. Ideal for a "why is service X down?" agent. | high | github.com/jonigl/mcp-client-for-ollama (primary) |

**Refuted / do not rely on** (killed in verification): specific single-model VRAM figures like "Qwen 3.6 27B Q4 ≈ 22 GB / 128 K" and "Codestral 22B ≈ 14 GB" (0-3); the localllm.in hybrid-attention/MoE-CPU-offload throughput numbers (0-3); "vLLM 44x at 64 users" and "single-user engine difference is all quantization" (both killed).

---

## Shared base infrastructure (both pillars sit on this)

Evolve the existing `local-ai-tooling` stack — don't restart. **This layer is live today** (see [Live state](#live-state-validation-2026-07-14)); the numbered items describe the intended shape, with live-vs-planned noted inline.

1. **Model server (LIVE):** keep **Ollama** (native/systemd) as the default GGUF server; *add (planned)* **llama.cpp `llama-server`** directly for the cases where you want explicit KV-cache/flash-attention/context flags Ollama hides. Both honor VRAM load/unload.
2. **Gateway (LIVE):** keep **LiteLLM** as the single OpenAI-compatible endpoint (one base URL for opencode, OWUI, agents, RAG). Keep `litellm-db` (**postgres:16-alpine**).
3. **UI (LIVE):** keep **Open WebUI** as the human chat/RAG front end.
4. **Tools bridge:** keep **mcpo** (MCP↔OpenAPI, **LIVE**) so MCP tools are reachable as plain HTTP for LiteLLM/OWUI; *add (planned)* **ollmcp** for the agentic approval loop (Pass B).
5. **Model set to pull** (names are *tiers* — verify current best at build time, the landscape drifts monthly). **Largely already pulled on the rig** (2026-07-14):
   - **Primary coder/agent:** a ~27B-dense-Q4 *or* ~30B-A3B-MoE-Q4 model strong at **both** code and tool-calling. 2026 candidates: Qwen3-Coder-30B-A3B, Devstral Small 2, GLM-class ~27B — **bench them for tool-call fidelity, not just code**. *(Live: `qwen3.6:27b` ≈17 GB, `qwen3.6:35b-a3b` ≈24 GB, `qwen3-coder:30b` ≈19 GB, `devstral:24b` ≈14 GB, plus a `code:opencode` tag are all present.)*
   - **Fast small model** (~7–14B) for autocomplete / cheap tool routing / the ops agent's inner loop (7B is the practical floor for reliable MCP tool selection). *(Live: `qwen2.5-coder:7b` ≈5 GB, `llama3.2:3b` ≈2 GB present.)*
6. **GPU-coexistence policy (⚠ under-verified — validate with a spike, see below):** the intended pattern is **AI yields to gaming**. Use Ollama `keep_alive` to unload models on idle (default ~5 min; `keep_alive: 0` = release VRAM immediately after a response; negative = never unload). Wire a **Sunshine/Apollo game-session start hook** to force-unload the LLM (set `keep_alive:0` / stop the server) so streaming + game servers get the full 24 GB, and reload on session end. MPS/time-slicing was **not** substantiated for a gaming+LLM mix — treat full-yield-during-gaming as the safe default, not concurrent sharing.
7. **Observability:** add LLM request logging via LiteLLM + a verification check (e.g. "LiteLLM `/health` + a canned completion returns < N s") mirroring the existing verification harness pattern.

---

## Plan Pass A — local AI software development (opencode + OWUI)

**Goal:** a Claude-Code-like agentic loop that's genuinely useful on local models. *(Planned — not yet deployed.)*

1. Point **opencode** at LiteLLM via an OpenAI-compatible provider block (`baseURL` → LiteLLM `/v1`, model keys matching the served model). opencode won't *recommend* a local model, but it *runs* any.
2. **Model selection is the whole game:** evaluate 2–3 candidate local models specifically on **agentic tool-calling reliability in a real repo loop** (multi-file edit → run tests → fix), not chat benchmarks. Keep the winner as the opencode default; keep a fast small model for autocomplete.
3. **Scope local work to its strengths:** single-file/bounded edits, test gen, boilerplate, refactors, code Q&A. Route "hardest multi-file/cross-repo/new-API" tasks to a human or accept lower success — **no cloud fallback by decision** (the AI-stack SPOF is an accepted decision).
4. **Alternatives to A/B** if opencode's local ergonomics disappoint: **Aider** (strong diff/edit discipline, repo-map), **Cline/Continue** (IDE-native). Worth a bake-off — Aider in particular is known to squeeze more out of weaker models.
5. OWUI stays the conversational/code-Q&A surface for non-agentic use.

## Plan Pass B — home-ops + Q&A agents + RAG

**Goal:** LAN-invokable skills + an ops agent ("why is service X down?") + doc Q&A. *(Planned — not yet deployed.)*

1. **Ops agent:** **ollmcp** driving a tool-using model over MCP servers that wrap read-only fleet inspection (systemctl/journal/health endpoints, the existing verification checks, healthchecks). **Human-in-the-loop approval on by default**; start read-only. Expose it on the Trusted VLAN only.
2. **Skills library:** package reusable skills as MCP tools behind mcpo so both OWUI and the agent loop can call them; version them in the `local-ai-tooling` repo.
3. **RAG over homelab docs/runbooks** (⚠ lower-confidence — no claim fully survived verification; validate the picks): a self-hosted embedding model **fits alongside** a 24B–27B Q4 LLM in 24 GB — candidates: **Qwen3-Embedding-0.6B (~2 GB)** or **BGE-M3 (1024-dim)**, optionally a **BGE-reranker-v2-m3** stage (+200–800 ms, +8–15 precision@3), served via **TEI**. Index this repo's `docs/` + `wiki/` into a vector store (OWUI's built-in RAG is the low-effort start); keep it fresh on a timer/commit hook. *(Note: an embedding model — `nomic-embed-text` — is already pulled on the rig, a viable low-effort starting point.)* **Treat model/dim/VRAM numbers here as unverified until a spike confirms.**
4. **Safety:** keep ops tools read-only until trusted; never expose the agent off the Trusted VLAN; approvals stay on for anything mutating.

---

## Honest limits & open questions (validate before committing hardware time)

The research was **thin or unverified** on four things — do a short validation spike for each before building on them:

1. **GPU coexistence mechanics** — measure the real VRAM-handoff latency of unload-on-game-start; confirm full-yield is needed vs any safe concurrent share.
2. **RAG stack fit** — confirm the actual embedding model + vector store + chunking that fits and performs alongside the coding model in 24 GB.
3. **exl2/TabbyAPI & SGLang on Ampere** — is exl2's speed/quant edge worth leaving the GGUF/Ollama ecosystem? (No FP8 on Ampere limits some options.) Not settled.
4. **Which single ~24–27B model is best at code AND tool-calling** for opencode — the deciding empirical question; run the bake-off.

---

## Live state validation (2026-07-14)

Checked against the live rig, `progress.json`, and the quality-hardening state at migration time:

- **GPU:** `nvidia-smi` reports **NVIDIA GeForce RTX 3090 Ti, 24564 MiB total** — the 24 GB hard ceiling is confirmed. (A model was loaded at check time; the "AI yields to gaming" idle-unload policy in item 6 is still a **planned** spike, not yet wired.)
- **Base infra containers up on the rig:** `litellm` (alive — `/health/liveliness` → "I'm alive!"), `litellm-db` (**postgres:16-alpine**, healthy), `open-webui` (healthy), `mcpo`. Ollama runs **natively** (not containerized). This matches the "shared base infra" section.
- **Models already pulled** (so item 5's "model set to pull" is substantially done): `qwen3.6:27b`, `qwen3.6:35b-a3b`, `qwen3-coder:30b`, `devstral:24b`, `code:opencode`, `qwen2.5-coder:7b`, `llama3.2:3b`, `nomic-embed-text` (embedding), among others.
- **opencode / ollmcp / RAG:** **not deployed** — no evidence in the repos or on the rig; Plan Pass A and B remain aspirational.
- **HA Assist integration (adjacent, already live):** Home Assistant's Assist uses the **rig Ollama directly** (`http://192.168.10.12:11434`, agent `conversation.rig_ollama_assist`, model `llama3.2:3b`) — delivered under the reliability workstream (queue 02 / #12), not part of this build. The default Assist pipeline is deliberately left on the intent engine so device control still works.
- **No fallback (by decision):** the earlier "LiteLLM on the mini" fallback was a phantom, never deployed and since deleted; the AI-stack single-point-of-failure (rig-only) is an **accepted** decision. Item A.3's "no cloud fallback" is intentional, not a gap.

---

## Sources & freshness

Primary: `opencode.ai/docs/models`, `github.com/jonigl/mcp-client-for-ollama`, vLLM docs, Red Hat Developer (2026-06-15). Benchmark blogs (hardware-corner, insiderllm, pactentia, promptquorum) for the VRAM/throughput tiers — internally consistent but blog-tier and version-dependent.

**⚠ Fast-moving:** specific model names (Qwen 3.6, GLM-5.2, DeepSeek V4, Devstral 2, GPT 5.2, Claude Mythos 5) and tokens/sec figures will drift within months — treat named models as *tier representatives*, re-check the current best at build time. Full report + citations: deep-research run `wf_3ac0bd51-ae9` (2026-07-13).

---
[← Architecture & design](index.md)
