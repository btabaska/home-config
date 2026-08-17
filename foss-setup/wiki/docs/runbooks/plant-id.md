# Plant / species identification (BioCLIP 2 + OWUI)

Fully-local organism identification (lai-22, 2026-08-16): snap a photo, attach it
to an Open WebUI chat, ask "what plant is this?" — no cloud API involved.

## How to use it (household)

1. Open **ai.tabaska.us** (Open WebUI) on phone or desktop.
2. Start a chat with any model. **chat** now has native vision (it sees your
   photo directly) *and* the tool; **coder** is the most reliable tool-caller
   (text-only — the photo goes to the tool, not the model). **cydonia /
   dolphin-venice / goetia** also have native vision.
3. Attach a photo of the plant (the `+`/paperclip button) and ask something like
   *"What plant is this? Use the identify_plant tool."* (On vision models you
   can also just ask about the photo conversationally — but for species-level
   ID trust BioCLIP over the LLM's eyeballing.)
4. The model calls the **identify_plant** tool, which finds the newest image in
   the chat and returns the top-k ranked taxa; the model narrates the best match
   with its common name and confidence.
5. Optional: ask for a coarser rank ("identify at genus level") — the tool
   accepts `species | genus | family | order | class | phylum | kingdom`.

Works for any organism (animals, fungi, insects), not just plants — the model
behind it covers ~925k taxa.

## Architecture

```
phone/browser → OWUI (rig :3000) → identify_plant workspace tool
                    │ (in-process: __messages__/__files__ → Files/Storage)
                    └─HTTP──▶ bioclip-api (rig :8199, docker) → BioCLIP 2
```

- **bioclip-api** — `local-ai-tooling docker/bioclip-api/` (FastAPI +
  pybioclip 2.1.6, BioCLIP 2 / TreeOfLife-200M). Lazy-loads the model on first
  `/identify`; weights (~2 GB) cache in the `bioclip_data` volume (offline
  afterwards). `GET /health`, `POST /identify?k=5&rank=species` (multipart
  `file`).
- **CPU inference BY DESIGN** (`BIOCLIP_DEVICE=cpu`): the 3090 Ti is fully
  budgeted for llama-swap — the big LLM lanes are measured <1 GiB-headroom edge
  fits, so a resident 2 GB CUDA context would break them. ViT-L/14 on CPU is
  ~0.6 s warm, ~20-30 s on first load. GPU mode = rebuild the image without the
  CPU torch index + set `BIOCLIP_DEVICE=cuda` + a `gpus:` reservation.
- **identify_plant tool** — DB-only (OWUI workspace tool). Canonical source:
  `local-ai-tooling owui-tools/identify_plant.py`, re-seeded idempotently by
  `scripts/seed-owui-identify-plant.sh` (same rebuild-parity contract as
  `seed-owui-tool-servers.sh`; key = vault `ai_stack.openwebui_rag_sync_api_key`).
  It resolves the newest chat-attached image (data-URI paste or uploaded file
  record, via the in-process Files/Storage API — verified against the 0.11.0
  backend) and POSTs it to `http://bioclip-api:8199`.

## Verification

Two-stage, `checks.d/local-ai.yaml`, both `tier: daily`:

- **bioclip-identify-consumer** — golden Wikimedia dandelion
  (`assets/plant-id-dandelion.jpg`) straight at rig `:8199`; top-1 **genus**
  must be `Taraxacum`. Genus on purpose: Taraxacum microspecies are genuinely
  ambiguous (top-3 all agree on genus), species-level would flap.
- **owui-plant-id-e2e** (`bin/owui-plant-id-e2e.py`) — the real household call
  path: upload via the OWUI files API → chat completion with
  `tool_ids=["identify_plant"]` → reply must name Taraxacum.

## Gotchas (hard-won)

- **API tool execution needs `stream: true` + `params.function_calling:
  "legacy"`.** On 0.11.0, native function calling only *executes* tools inside
  UI sessions (`session_id` present) — a raw `/api/chat/completions` caller gets
  the unexecuted `tool_calls` deltas back. Legacy mode runs
  `chat_completion_tools_handler` server-side pre-completion. UI chats are
  unaffected (native mode works there).
- **The `chat` lane VRAM story (2026-08-16, two rounds).** Round 1: gemma at ctx
  73728 stopped fitting once desktop residents grew (ComfyUI's CUDA context +
  Apollo NVENC + Steam/kwin ≈ 0.8 G) — `upstream command exited prematurely` —
  fixed by trimming to 65536. Round 2 (same day): native **vision** added — the
  unsloth mmproj-F16 (1.2 G, sha256-verified in models.manifest) needed another
  trim to **49152** (57344+mmproj OOMed at the 1.14 G clip buffer; final board
  ≈ 24.0 G, ~0.5 G headroom — same margin class as the Mistral trio). Rule of
  thumb: only 10/60 gemma layers are global attention, so each 8 k of ctx frees
  ~340 M KV + buffer growth. If a load-fail recurs, ctx is the knob.
- **Vision capability flags must be TRUTHFUL** — the OWUI frontend embeds
  attached images as `image_url` parts only when the model record says
  `vision=true`; a lying flag is exactly the household's
  `image input is not supported ... mmproj` 500, and a missing flag hides real
  vision. Flags are DB-only; canonical source =
  `local-ai-tooling scripts/seed-owui-model-capabilities.sh`
  (vision=true: chat, rig-thinker, cydonia, dolphin-venice, goetia; everything
  else false). NOTE the 0.11 models/tools APIs both want `access_grants` (list),
  not the old `access_control`.
- Guarded by **owui-chat-vision** (`bin/owui-chat-vision.py`, daily): sends the
  golden image as an image_url part through OWUI to `chat` and requires a
  plant-ish description back.
- **Tool returns "No attached image found"** → the user asked before attaching,
  or the attachment isn't an image. Attach the photo and re-ask in the same
  chat.
- **First identify after a volume wipe is slow** — it re-downloads ~2 GB of
  weights from Hugging Face; needs outbound internet once.
