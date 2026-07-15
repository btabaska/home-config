# Local-AI build — SHIPPED

> The homelab's local-first AI stack on the rig's single RTX 3090 Ti (24 GB):
> llama.cpp/llama-swap model serving, LiteLLM gateway, agentic coding
> (opencode/pi), an ops agent with read-only fleet tools, and wiki RAG.

_Source: `foss-setup/docs/local-ai-build-plan.md` → executed as `ai-01`._

**Status: SHIPPED 2026-07-15** (built + demonstrated live 2026-07-14/15; every
acceptance criterion below verified against the running fleet). The original
research/design content is kept as an appendix at the bottom — where it and
this section disagree, this section is the live truth.
**Stack repo:** `local-ai-tooling` on the rig (`~/Documents/GitHub/local-ai-tooling`); checks + tracker live here in `foss-setup`.

---

## TL;DR — what shipped, and honest expectations

**Ollama was decommissioned as the model server** and replaced by
**llama-swap + llama.cpp `llama-server`** (Docker, CUDA via CDI) behind the
existing **LiteLLM** gateway. A 3-model **Ollama compat shim** remains on
`:11434` *only* for HA Assist and Obsidian. Coding default is
**Qwen3.6-35B-A3B** (bake-off winner: 3/3 agentic tasks, **0 malformed tool
calls**, 73–126 tok/s); **Qwen3.6-27B** is the strong/slow fallback. GPU
yields to gaming via idle-unload + an Apollo session-start force-unload hook
(**182 ms** measured VRAM handoff).

Expectations (unchanged from the research, confirmed in practice): local
covers **~80% of bounded daily coding** (single/multi-file edits, tests,
refactors, boilerplate) as a **supervised** coder — it is not an autonomous
frontier replacement; route the hardest cross-repo/new-API work to a human.
No cloud fallback, by decision. Rig down = AI down (accepted SPOF).

## Architecture (as built)

```
any LAN/tailnet machine
  ├── opencode / pi  ──►  https://llm.tabaska.us  (LiteLLM :4000, virtual keys)
  ├── browser        ──►  https://ai.tabaska.us   (Open WebUI :3000)
  ├── llama-swap UI  ──►  https://llamaswap.tabaska.us (:9292, activity/unload)
  └── HA Assist / Obsidian ──► ollama SHIM :11434 (llama3.2:3b · tag:fast · nomic)
                                     │
rig (192.168.10.12) ─ docker compose │ (local-ai-tooling/docker/)
  LiteLLM :4000 ──► llama-swap :8080(→9292) ──► llama-server (one proc/model,
  CUDA via CDI, on-demand load, ttl idle-unload, swap group = 1 big model at
  a time + persistent CPU embedder)
  fleet-mcp :8765 (systemd, host) ──► read-only ops tools (ssh fleet-mini/nas)
  mcpo :8000/fleet ──► same tools bridged to Open WebUI
```

**LiteLLM aliases** (stable public names; clients never change when models do):

| alias | model (llama-swap) | use |
|---|---|---|
| `coder` (=`code`) | qwen3.6-35b-a3b UD-IQ4_NL_XL 32k | agentic coding default |
| `coder-strong` | qwen3.6-27b UD-Q4_K_XL 32k | long/hard tasks (slower, steadier) |
| `chat` | gemma4-31b-qat 16k | general chat |
| `chat-creative` | deckard-heretic 8k | creative |
| `fast` | qwen2.5-coder-7b 32k | autocomplete/cheap tool loop |
| `utility` | fast-3b (llama3.2, temp 0) | titles/tags/classification |
| `embed` | Qwen3-Embedding-0.6B Q8 (CPU, `--pooling last`, instruct query prefix) | RAG embeddings |

Model files live in `/opt/llm/models` — **deliberately outside /home** so
restic never backs up re-pullable weights (removed ollama blobs are hardlink-
archived in `/opt/llm/models/archive/`). Configs are the backup: everything
is in the two repos.

**Gotcha fixed en route:** the ollama-pulled qwen3.6 blobs were **Ollama-fork
GGUFs** (metadata incompatible with mainline llama.cpp — the lock-in the
migration was escaping); both were re-pulled as unsloth GGUFs from HF. All
other blobs were mainline-clean and are served directly (hardlinks, zero copy).

## Bake-off (spike d) — measured on this card

Real repo loop (edit → run tests → fix) over function-calling tools; three
tasks incl. a multi-file feature and a 3-part refactor with traps. Harness +
results: `local-ai-tooling/bakeoff/`.

| model | tasks | malformed calls | avg turns | tok/s |
|---|---|---|---|---|
| **qwen3.6-35b-a3b** ← winner | 3/3 | 0 | 6.0 | 73–126 |
| qwen3.6-27b | 3/3 | 0 | 6.7 | 23–31 |
| qwen3-coder-30b | 3/3 | 0 | 10.7 (churny) | 59–145 |
| devstral-24b | 0/2 | — | never engaged tools | — |

Notable: qwen3-coder-30b's "malformed tool calls" reputation under Ollama did
not reproduce under llama-server `--jinja` — the migration itself fixed the
tool-call formatting class. The 35B winner also ran clean in the real opencode
demo (no chopped-args issue at 8192 max output tokens).

## Spike outcomes

- **(a) GPU yield:** unload-all returns in ~170 ms; VRAM 22.4 GiB → baseline
  in **182 ms**. Warm reload 1.3–3.3 s; cold-after-boot 11 s. Full-yield is
  the policy (no concurrent share needed): llama-swap `ttl` (120 s big / 300 s
  small / 3600 s embed) + `scripts/gpu-yield-unload.sh` wired as Apollo
  `global_prep_cmd`. Caveat: an in-flight generation delays the unload until
  it finishes; the hook never blocks session start (3 s cap, always exit 0).
- **(b) RAG fit:** proven, then improved: the final embedder
  (Qwen3-Embedding-0.6B) runs on **CPU** (`-ngl 0`) — at the 8k batch sizes
  long chunks need, its GPU compute buffers ate ~6.5 GB and crowded the
  19.7 GB coder. On CPU it never contends with models or games, and query
  latency is negligible. RAG sync runs freely while someone codes.
- **(c) exl2/TabbyAPI/SGLang on Ampere:** evaluated; **stay GGUF/llama.cpp**.
  exl2/exl3 has a real single-user speed edge on paper, but: no FP8 on Ampere,
  exl quants for week-old models lag GGUF (unsloth ships day-one; MTP variants
  are GGUF-only), and llama-swap can front TabbyAPI later if that ever flips.
- **(d)** the bake-off above.

## Ops pillar (`local-ai-tooling/ops/`)

- **fleet-mcp** (`fleet-mcp.service`, rig `:8765/mcp`): READ-ONLY fleet tools —
  service status/journals/containers/system overview for rig+mini+nas (ssh,
  `from=`-restricted key), internal URL checks, the verification harness,
  GPU/model status, healthchecks summary. Read-only **by construction**
  (validated args, no arbitrary-command tool). Trusted-VLAN-only (UFW).
- **ollmcp** (`ops-agent.sh`): interactive agent TUI → LiteLLM `coder` →
  fleet tools, human-in-the-loop approval ON.
- **Open WebUI**: same tools via mcpo (`fleet` external tool server).
- **ops_probe.py**: non-interactive bounded loop (drives the liveness check).
- **Demonstrated:** synthetic failed unit diagnosed to root cause (missing
  config file) with cited evidence in 3.5 s, 2 tool calls.

## RAG pillar

OWUI knowledge collection **`homelab-wiki`** (RAG embeddings via LiteLLM
`embed` → Qwen3-Embedding-0.6B; nomic was dropped mid-build — its 2048-token
trained context rejected big markdown-header chunks), synced
daily at 05:10 from the forgejo repo by `wiki-rag-sync.timer` on the mini
(`/opt/verification/bin/wiki-rag-sync.py`, incremental by sha256 manifest;
source in `foss-setup/scripts/ai/`). Reference it in chat with
`#homelab-wiki`. Freshness is check-guarded (`mini-wiki-rag-fresh`).

## Observability

- checks (`verification/checks.d/rig.yaml`, all deployed + negative-tested):
  `rig-llama-swap` (fast tier), `rig-llama-swap-models`, `rig-ai-gpu-yield`
  (behavioral: on-demand load + VRAM frees), `rig-fleet-mcp`,
  `rig-mcpo-fleet-tools`, `rig-ops-agent-e2e` (bounded agent loop),
  `rig-ollama`/`rig-ollama-models` (re-scoped to the shim + HA's model),
  `rig-ollama-keepalive` (shim), `rig-litellm`, `rig-ai-e2e` (also the canned
  completion latency budget), `mini-wiki-rag-fresh`.
- `ai-stack-watchdog` (rig, 10 min): now probes BOTH docker→host hops
  (:11434 shim and :8765 fleet-mcp) — the UFW docker-subnet regression class.
- LiteLLM request/spend logging per virtual key (`open-webui`, `opencode`,
  `ops-agent`) in Postgres — see `https://llm.tabaska.us/ui`.
- `llm-triage.sh` (mini) repointed at llama-swap `:9292` / qwen3.6-35b-a3b.

## Acceptance criteria — demonstrated live 2026-07-15

1. ✅ opencode from the Mac over `llm.tabaska.us` fixed a 3-part failing repo
   (incl. writing a bracket-depth parser) in 32 s wall, 10/10 tests green.
2. ✅ ops agent root-caused a failed service via read-only tools (HIL in
   ollmcp; ops_probe for the scripted proof).
3. ✅ Model switching transparent (aliases; llama-swap loads on demand).
4. ✅ GPU yield: 182 ms handoff; Apollo hook registered + logs to journal.
5. ✅ Reboot survival: full stack (9 containers + ollama shim + fleet-mcp +
   apollo) back unattended in ~76 s; first request auto-loads (11 s cold).
6. ✅ HA Assist verified after the trim (`conversation.rig_ollama_assist`
   answered via `POST /api/conversation/process`).
7. ✅ Auth on: LiteLLM master + per-client virtual keys (vault: `ai_stack.*`);
   ops surface Trusted-VLAN-only.

## How to use it (daily-driver notes)

- **Coding (bounded tasks):** `opencode` anywhere on LAN/tailnet — config in
  `~/.config/opencode/opencode.json` (Mac + rig deployed; template in
  `local-ai-tooling/clients/`). Default `litellm/coder`; switch to
  `coder-strong` for long/gnarly work; `pi` is configured on the rig as the
  minimal-harness alternative (`~/.pi/agent/models.json`).
- **Chat / homelab Q&A:** `https://ai.tabaska.us`, `#homelab-wiki` for
  wiki-grounded answers; the `fleet` tool server for live fleet questions.
- **Ops diagnosis:** `ssh rig -t '~/Documents/GitHub/local-ai-tooling/ops/ops-agent.sh'`
  (approve each tool call), or `ops_probe.py "question"` for one-shots.
- **Good at:** single/multi-file edits with tests, boilerplate, refactors,
  code Q&A, tool-driven diagnosis. **Bad at:** 100k-token cross-repo
  reasoning, brand-new APIs, unsupervised long runs — hand those to a human.
- **Gaming:** just play — the Apollo hook frees VRAM at session start; the
  LLM reloads on the next request.

## Follow-ups (tracked, optional)

- **MTP speculative decoding** for `coder-strong`: mainline llama.cpp supports
  Qwen3.6 MTP (b9180+; running b9994). Recipe: `unsloth/Qwen3.6-27B-MTP-GGUF`
  UD-Q4_K_XL + `--spec-type draft-mtp --spec-draft-n-max 2..3 -np 1`, q8_0 KV,
  and benchmark the exact `--ctx-size` (avoid 2048-aligned values — llama.cpp
  #23658 acceptance collapse). Reported 1.7× gen on a 3090 (38→65 tok/s).
- **Devstral Small 2 (2512)** as a non-Qwen fallback pull if wanted.
- OWUI: attach `#homelab-wiki` to a custom model for a dedicated "Homelab"
  assistant (UI step, operator taste).
- Pre-existing (NOT ai-01): `restic-snapshot-fresh-rig` false-positive — the
  `/var/lib/restic/last-success` marker isn't being touched although backups
  run green (last real snapshot 2026-07-15 01:40).

---

## Appendix — original research & design (2026-07-13/14, pre-build)

### The honest verdict (research)

A local-only build on this 24 GB card can serve **~80% of day-to-day coding**
(single-file edits, bug fixes, test generation, boilerplate, refactors) and
**reliable tool-using ops/Q&A agents** — but it **cannot reach frontier
parity**. The 2026 leaderboard-topping coders are 700 B–1 T MoE models needing
200 GB+ VRAM; self-hostable-in-24 GB models top out ~68–77% SWE-bench Verified
vs 80–95% for frontier cloud — a **17–27-point gap**, concentrated in
post-training-cutoff API knowledge, 100 k+-token multi-file reasoning, and
debugging accuracy. **Local is the daily driver for bounded work; it is not a
Claude-Code replacement for the hardest multi-file/cross-repo tasks.**
[high confidence — 3-0 verified]

### Verified findings (survived 3-vote adversarial verification)

| # | Finding | Conf. |
|---|---|---|
| 1 | **No frontier parity on 24 GB.** Local 24 GB tops ~68–77% SWE-bench vs 80–95% cloud; handles ~80% of daily work. | high |
| 2 | **VRAM tiers (this card):** 27B dense Q4 ≈ 17 GB weights (room for KV + co-located small model); 30–35B-A3B MoE Q4 ≈ 18–24 GB; 32B dense Q4 ≈ 23.4 GB / ~12 K ctx only. | med → **confirmed live**: 27B UD-Q4_K_XL = 19.0 GiB @32k, 35B-A3B UD-IQ4_NL_XL = 19.7 GiB @32k |
| 3 | **Runtime: llama.cpp over vLLM here** — single-user parity, and vLLM pre-grabs ~90% VRAM (starves streaming). | high → adopted (llama-swap manages load/unload) |
| 4 | **opencode + local:** works via OpenAI-compatible `baseURL`; few models do code+tools both well — pick for that. | high → bake-off run |
| 5 | **ollmcp** for the safe LAN ops agent (HIL approvals over MCP tools). | high → shipped |

Refuted / do-not-rely-on (killed 0-3 in verification): specific single-model
VRAM figures ("Qwen 3.6 27B Q4 ≈ 22 GB/128 K", "Codestral 22B ≈ 14 GB"),
localllm.in hybrid-attention/MoE-offload throughput numbers, "vLLM 44× at 64
users".

### Sources & freshness

Primary: `opencode.ai/docs/models`, `github.com/jonigl/mcp-client-for-ollama`,
vLLM docs, Red Hat Developer (2026-06-15); benchmark blogs (hardware-corner,
insiderllm, pactentia, promptquorum). Bake-off/MTP field check 2026-07-15:
unsloth qwen3.6 docs, llama.cpp issues #23658/#23322/#23233, HF Qwen
discussions. Deep-research runs `wf_3ac0bd51-ae9` (2026-07-13) +
`wf_1aebd444-6a6` (2026-07-15). **Model names/figures drift within months —
re-check at upgrade time.**

---
[← Architecture & design](index.md)
