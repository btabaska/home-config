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
calls**, 73–126 tok/s); **Qwen3.6-27B (MTP, ~50 tok/s)** is the strong
fallback. GPU
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
| `coder` (=`code`) | qwen3.6-35b-a3b UD-IQ4_NL_XL **256k ctx (native max)** | agentic coding default |
| `coder-strong` | qwen3.6-27b **MTP** UD-Q4_K_XL **112k ctx** (~50 t/s) | long/hard tasks |
| `chat` | gemma4-31b-qat 72k | general chat |
| `chat-creative` | deckard-heretic 48k | creative |
| `cydonia` | Cydonia-24B-v4.3 Q5_K_M **60k + vision** | storytelling / roleplay (#1 pick) |
| `dolphin-venice` | Dolphin-Mistral-24B-Venice Q5_K_M **60k + vision** | uncensored, system-prompt-steered |
| `goetia` | Goetia-24B-v1.3 Q5_K_M **60k + vision** | dark / edgy roleplay |
| `fast` | qwen2.5-coder-7b 32k (native max) | autocomplete/cheap tool loop |
| `utility` | fast-3b (llama3.2, temp 0) 128k (native max) | titles/tags/classification |
| `embed` | Qwen3-Embedding-0.6B Q8 (CPU, `--pooling last`, instruct query prefix) | RAG embeddings |

Ctx sizes above are the **measured VRAM ceilings** (2026-07-16 full-fleet
bake-off, q8_0 KV + flash-attn, embedder truly CPU-pinned): every model now
runs the max ctx that loads fully on GPU, or its native max if that fits.
Each entry also bakes its HF-model-card recommended sampling defaults into
llama-swap (`--temp/--top-p/--top-k/...`), mirrored in the OWUI model params.
Enabler discovered en route: `-ngl 0` alone still left ~2.8 GiB of CUDA batch
buffers on the card for the embedder — `CUDA_VISIBLE_DEVICES=""` in its
llama-swap `env` freed it and raised every big model's ceiling.

The three creative/RP models (`cydonia`, `dolphin-venice`, `goetia`, added
2026-07-18) are all Mistral-Small-3.2-24B Q5_K_M served with the Mistral v7
"Tekken" template (embedded, via `--jinja`) plus DRY sampling for long-chat
repetition. **Vision is enabled** (2026-07-18): one shared Mistral-Small-3.2-2506
vision tower (`mmproj-mistral-small-3.2-f16.gguf`, 838 MB) serves all three
finetunes via `--mmproj`, so image attachments work in Marinara/Lumiverse/OWUI.
The tower + compute buffer cost ~1.3 GiB, so ctx runs **61440** (the text-only
measured ceiling was 73728 at 22.8 GiB / 1.2 GiB free, 81920 OOMs —
`bakeoff/ctx-ceiling-probe.sh`; 65536+mmproj left only 0.5 GiB free). All three
byte-identical Q5 24B, so an identical ceiling (edge fit, gaming force-unload is
the safety valve). Dolphin-Venice ships near-unaligned: its behavior is set by
the **system prompt**, and its card's temp 0.15 (factual use) is deliberately
overridden to 0.7 here for creative/RP.

**Two creative/RP web frontends ride LiteLLM for these models** (added
2026-07-18): **Lumiverse** (`ghcr.io/prolix-oc/lumiverse`, pinned by digest;
`lumiverse.tabaska.us` → rig `:3001`) and **Marinara-Engine**
(`ghcr.io/pasta-devs/marinara-engine:1.5.0`, alpha; `marinara.tabaska.us` → rig
`:3002`), both in the same `local-ai-tooling/docker` compose. Neither has a
server-side model allowlist, so each is pointed (via an **in-app** Custom
OpenAI-compatible connection — `http://litellm:4000/v1`) at a **per-app LiteLLM
virtual key scoped to exactly `cydonia`/`dolphin-venice`/`goetia`** — that key
*is* the model restriction. Two security notes drove the config: Lumiverse has
a live critical-CVE history (pin a patched image, LAN/tailnet-only), and
Marinara's own Basic Auth is void behind Docker's userland-proxy (it only ever
sees a trusted private/Docker source IP), so its auth is enforced at the **mini
Caddy** vhost with `basic_auth` instead. Keys/secrets live in the rig `.env` +
vault `ai_stack.*`; the end-to-end path (frontend → LiteLLM key → llama-swap →
model, with non-scoped models rejected 403) was validated live at deploy.

## Image generation (ComfyUI, added 2026-07-18)

**ComfyUI** (`mmartial/comfyui-nvidia-docker`, CDI GPU, `:8188`,
`comfyui.tabaska.us`) is the RP image-gen backend, in the same
`local-ai-tooling/docker` compose. Three stacks, all verified generating
end-to-end (models in `/opt/comfyui/models`, outside /home like /opt/llm):

| stack | model | ComfyUI recipe (default, post 2026-07-19 quality pass) | ~time / peak VRAM |
|---|---|---|---|
| realistic | Z-Image Turbo (`Comfy-Org/z_image_turbo`) | UNET + **`lumina2`** CLIP (qwen_3_4b) + ModelSamplingAuraFlow sh3, **`dpmpp_sde`/`beta`**, 8 steps cfg 1, **native 1328²** | ~26 s / 21.8 GiB |
| anime | NoobAI-XL 1.1 (`Laxhar/noobai-XL-1.1`, Illustrious **EPS**) | standard SDXL, `euler_a`/`normal`, **30 steps cfg 5.5, 832×1216**, canonical Danbooru quality tags + official negative | ~10 s / 19 GiB |
| realistic alt | Flux.2 Klein **distilled** 9B (`unsloth/FLUX.2-klein-9B-GGUF`, `flux2` CLIP qwen_3_8b) | GGUF UNET + SamplerCustomAdvanced, **6 steps cfg 1** (distilled model at its intended config — was mis-run at 20/cfg4) | ~15 s / 19 GiB |

A single image model peaks **~21 GiB** and the 73k-ctx 24B LLMs sit at
**~22.8 GiB**, so they can't co-reside. The **gpu-arbiter** (`:8189`,
`docker/gpu-arbiter.py`) is a transparent ComfyUI reverse proxy that enforces
**take-turns**: on `POST /prompt` it force-unloads llama-swap (the existing
182 ms gpu-yield endpoint); when ComfyUI's queue drains it POSTs `/free` so the
LLM reloads on the next chat turn. Frontends point their ComfyUI URL at
**`:8189`, not `:8188`**. Verified API workflows: `local-ai-tooling/comfyui-workflows/`.

**Quality pass (2026-07-19, deep-research-backed, all re-validated + re-seeded
into both frontends).** The three defaults above were tuned for best per-pass
quality while staying fast enough for interactive RP. The **biggest fix was
Flux**: `unsloth/FLUX.2-klein-9B-GGUF` is the *distilled* (4-step) model, but it
was mis-run at the *base* model's 20 steps / cfg 4 → "overcooked" output + ~10×
wasted compute; the default now runs it at its intended **6 steps / cfg 1**. For
max fidelity the **base** 9B GGUF (`unsloth/FLUX.2-klein-base-9B-GGUF`, 24 steps
cfg 4, ~146 s) ships as an HQ variant. **HQ variants** live in
`comfyui-workflows/hq/` — hires-fix (4x-UltraSharp 2nd pass) + Impact-Pack
`FaceDetailer` (yolo `face_yolov8m`) for the two portrait models (z-image-hq peaks
23.6 GiB — edge fit) and the base-Flux variant. `comfyui-workflows/gen-workflows.py`
regenerates all raw + Marinara-`%placeholder%` variants. FaceDetailer needs the
ComfyUI-Impact-Pack + Impact-Subpack nodes with `opencv`+`ultralytics` installed
in the venv **as uid 1000** (same pattern as gguf).

**Prompt crafting (Open WebUI).** Image models need two different prompt
grammars — NoobAI is Danbooru **tags**, Z-Image/Flux are **natural language** —
and OWUI's built-in image-prompt task is single-global, so two Workspace model
presets do the job (base `chat`): **🏷️ Illustrious Tagger** (temp 0.4, emits
ordered tags + a NEGATIVE line) and **🎨 Scene Describer** (temp 0.6, emits a
cinematic prose paragraph). Draft in RP chat → `@`-mention the matching preset →
paste its output into the image connection.

**NSFW realistic stack (2026-07-19).** Anime NSFW needs no extra model (NoobAI-XL
is Danbooru/e621-native — drop `nsfw` from the negative). For **realistic** NSFW,
Z-Image retrains were pulled from Civitai (token now at vault `civitai.api_key`,
downloaded with `?token=` query-param + a browser UA — Bearer-on-CDN-redirect 400s)
plus the **uncensored `Qwen3-4b-Z-Image-Engineer-V4` Q8** text encoder (the biggest
NSFW-scene-understanding lever; loaded via `CLIPLoaderGGUF` type `lumina2`):
**CyberRealistic Catalyst v2.0 NSFW** (Z-Image *Turbo*, 8/cfg1, ~32 s) is wired into
both frontends as "Realistic NSFW (CyberRealistic)"; **Moody Wild V4** (Z-Image
*BASE* — needs 40 steps/cfg 4 + a real negative, ~76 s) is an `hq/` raw workflow.
(Moody Real was downloaded but is architecturally incompatible — `cap_embedder`
2560 vs 1280 — and dropped.) Seeders: `scripts/seed-{marinara,lumiverse}-connections.sh`. GGUF loading needs the ComfyUI-GGUF node + its `gguf` pip dep installed
into the venv **as uid 1000** (the `WANTED_UID` owner; the container's default
shell user 1025 can't write the venv).

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

## Context ceilings + MTP (measured 2026-07-15, post-ship increment)

The shipped 32k ctx was conservative — ladder-probed the real VRAM ceilings
(q8 KV + FA, total board memory incl. desktop):

| ctx | 35B-A3B (coder) | 27B (coder-strong) |
|---|---|---|
| 49k | 20.0 GiB | 19.6 GiB |
| 98k | 20.6 GiB | 21.5 GiB |
| 131k | **21.1 GiB ← shipped** | 22.7 GiB |
| 163k | — | 24.0 GiB (hard edge) |
| 262k (native) | **22.8 GiB — fits!** | — |

The MoE's KV is ~14 KiB/token (hybrid attention) vs ~38 KiB/token dense.

**Superseded by the 2026-07-16 full-fleet bake-off** (post btrfs-recovery
restore; embedder truly CPU-pinned via `CUDA_VISIBLE_DEVICES=""`, which
returned ~2.8 GiB to the pool). Measured max ctx per model, all verified
loading + generating fully on GPU: `coder` (35B-A3B) **262144 = native max**;
`coder-strong` (27B MTP) **114688**; qwen3-coder-30b 98304; devstral 98304;
`chat` (gemma4-qat) 73728; `chat-creative` (deckard) 49152; `fast` 32768
(native); `utility` 131072 (native). These are edge fits (<1 GiB headroom) —
the gaming force-unload hook is the safety valve. HF-card sampling defaults
are baked into each llama-swap entry and mirrored in OWUI model params.

**MTP speculative decoding: promoted.** A/B bench (900-token code gen, 2 runs
each): baseline 34.5 tok/s → **50.3 tok/s at `--spec-draft-n-max 2`** (1.46×);
n-max 3 was slower (47.2); the llama.cpp #23658 2048-aligned-ctx acceptance
bug did **not** manifest on b9994 (aligned ≡ non-aligned), prefill cost ~7%.
Correctness gate: the bake-off refactor task re-run on the MTP build —
success, 0 malformed tool calls, **47.4 tok/s in the real agentic loop**
(was 27.5; wall 85.9 s → 52.0 s, 1.72×). Caveats now living in the llama-swap
config comment: `--parallel 1` required; never send images through the MTP
entry (llama.cpp #23233); q8_0 KV benched clean but has one upstream
long-soak crash report — drop the cache-type flags first if it ever wedges.

## Follow-ups (tracked, optional)

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
