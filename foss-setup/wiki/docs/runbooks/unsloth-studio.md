# Unsloth Studio (run/train models, web UI)

Unsloth Studio on the rig (lai-28, 2026-08-17): the browser/web-UI form of
"Unsloth Desktop" — chat with local models, fine-tune, and export, all
self-hosted. **https://unsloth.tabaska.us** (mini Caddy → rig `:8210`), also on
the Homepage AI group. Login: user `unsloth`, password at vault
`ai_stack.unsloth_studio_password`.

## What it's wired to

```
laptop ── unsloth.tabaska.us ──▶ unsloth-studio (rig :8210, docker)
                                   │ provider "llama-swap (rig lanes)"
                                   ├──▶ llama-swap :8080/v1  (chat, coder…, qwen3.8-27b)
                                   │ scan folders (read-only)
                                   ├──▶ /models/gguf    = /opt/llm/models
                                   ├──▶ /models/comfyui = /opt/comfyui/models
                                   │ MCP servers (same as OWUI chat)
                                   └──▶ fleet · comfyui(arbiter) · playwright · memos
```

- **Text models are NOT loaded by Studio.** The saved `llama_cpp` provider
  points at `http://llama-swap:8080/v1`; pick lanes under **External** in the
  model dropdown. Params stay server-side in `llama-swap-config.yaml` —
  **qwen3.8-27b runs ctx 98304 with the thinking sampler set (temp 1.0 /
  top-p 0.95 / top-k 20 / min-p 0) and `--reasoning-effort medium`**; its HF
  card's "262k native" does NOT fit the 24 GB card, ctx is deliberately
  conservative. Loading a big GGUF *inside* Studio duplicates VRAM llama-swap
  already budgets — don't, outside of experiments.
- **MCP tools in chat**: the four native-MCP servers OWUI also uses (fleet
  inspection, ComfyUI image gen via the gpu-arbiter, Playwright browsing,
  Memos journal w/ bearer PAT). The mcpo bridges (time/fetch/openzim/
  sequential-thinking) are OpenAPI, not MCP — they cannot be wired here.
- **Diffusion**: the scan folders surface the ComfyUI library. Z-Image
  (`z_image_turbo_bf16` + cyberrealistic/moody finetunes), FLUX-2-klein GGUFs
  and the Krea2/Qwen-Image fp8 all validate in Studio; **this image build
  (backend 2026.5.9) has no image-gen route**, so actual generation goes
  through ComfyUI — from Studio chat, use the ComfyUI MCP tools
  (`zimage_turbo`, `noobai_anime`). **LTX-2.3 stays ComfyUI-only** (see
  gotchas). Audio: our TTS/STT are services (Kokoro, faster-whisper), not
  model files — Studio can pull its own audio models into the persistent HF
  cache if ever needed.
- **API**: OpenAI-compatible `/v1/chat/completions` (+ Anthropic
  `/v1/messages`) with an `sk-unsloth-…` key (vault `ai_stack.unsloth_api_key`,
  named "verification"). Provider routing needs `provider_id` +
  `external_model` in the payload (x-unsloth extensions).

## Config & rebuild parity

Everything in-app is **DB-only** (`unsloth_studio_data` volume:
`/workspace/studio/studio.db` + `auth/auth.db`). Canonical source:
`local-ai-tooling scripts/seed-unsloth-studio.py` (provider, scan folders,
MCP servers, API key; idempotent — run with `UNSLOTH_STUDIO_PASSWORD` +
`MEMOS_MCP_TOKEN` from the vault). Compose service: `local-ai-tooling
docker/docker-compose.yml` (`unsloth-studio`, digest-pinned, CDI GPU, web UI
`:8210` only — Jupyter `:8888`/SSH stay unpublished).

**After a volume wipe**: first boot writes a diceware passphrase to
`/workspace/studio/auth/.bootstrap_password` (the `UNSLOTH_STUDIO_PASSWORD`
env is IGNORED by this build). Read it in-container, log in, POST
`/api/auth/change-password` to the vault password (the file self-deletes),
re-mint the API key into the vault, then run the seed.

## Verification

- **unsloth-studio-e2e** (`bin/unsloth-studio-e2e.py`, daily): the real
  consumer chain — API key → `/v1/chat/completions` → provider →
  llama-swap → `qwen3.8-27b` → marker reply — plus a config drift gate
  (1 llama_cpp provider, both scan folders, ≥4 MCP servers).

## Gotchas (hard-won)

- **GPU contention**: Studio-loaded models (its own llama-server or future
  diffusion) are NOT governed by the gpu-arbiter. The provider path avoids
  this for text; anything Studio loads itself takes turns manually — unload
  llama-swap first (`POST rig:9292/api/models/unload`) and prefer daytime
  (Immich ML may hold the card 01–07 EDT).
- **Do not `validate`/load `ltx2310eros_v14.safetensors`** — the 29 GB
  single-file checkpoint gets the backend SIGKILLed (OOM-class) mid-parse;
  supervisord respawns it in ~10 s but in-flight requests die. Studio's LTX
  support expects HF-format repos, not ComfyUI monoliths.
- **Provider type must be `llama_cpp`** — it's a *hidden* registry entry
  (absent from `GET /api/providers/registry`; the frontend surfaces it via
  CUSTOM_PROVIDER_PRESETS). Wiring the server as type `openai` "works" but
  its model allowlist (`^gpt-5.x/o3`) filters every lane out → empty picker.
- `/v1/chat/completions` streams SSE even with `stream: false` — parse
  accordingly.
- The image auto-downloaded a small `gemma-4-E2B-it-GGUF` starter model into
  the HF cache on first boot (~3 GB, persisted in `unsloth_work`) — harmless.
- Port `:8000` on the rig belongs to **mcpo**; Studio's container port 8000 is
  published as `:8210`.
