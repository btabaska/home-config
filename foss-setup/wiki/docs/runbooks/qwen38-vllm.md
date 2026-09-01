# Qwen3.8-27B vLLM option lane (qwen38-27b-rtx3090)

Fast single-GPU serving of the same Qwen3.8-27B the rig already runs on
llama-swap, using the [syv-ai/qwen38-27b-rtx3090](https://github.com/syv-ai/qwen38-27b-rtx3090)
stack (patched vLLM 0.27.1, int8 tensor-core GEMMs, MTP/DFlash2 speculation,
150k-262k context). Single-user decode ~120-133 tok/s vs the llama-swap lane's
~55 t/s. **Hosted as an option: image + model are prepared on the rig, the
service is STOPPED by default** — one GPU, one server at a time, and
llama-swap owns the 3090.

(lai-29, 2026-09-01. Configured exactly per the repo's quick start: stock
`--profile single` defaults, no speculative-decode overrides.)

## Layout (live, on the rig)

- `/opt/stacks/qwen38-27b-rtx3090/` — git clone of the upstream repo
  (shallow, `main`). The compose project IS the repo root.
- `.env` (600, gitignored) — `VLLM_API_KEY` only. Key lives in the vault at
  `ai_stack.vllm_qwen38_api_key`; regenerate by writing a new line there and
  re-piping to the rig's `.env` (never paste the value into chat/commits/docs).
- `models/` (~22 GB) — `Qwen3.8-27B-W4A16-AutoRound` (int8-requantized in place
  by `prepare/`), `-fast` variant, and the `Qwen3.8-27B-DFlash2-W4A16` drafter.
  Prepared by `docker compose run --rm prepare` — **CPU-only, idempotent, safe
  to run while llama-swap owns the GPU** (each step skips when done).
- `qwen-cache` docker volume — torch.compile / Triton / FlashInfer JIT caches;
  first serve after a wipe is slow (healthcheck `start_period` is 900s).
- Port **18020**, served model name **`qwen3.8-27b`** (same name as the
  llama-swap lane — switching a client is a base_url change only).
- OpenAI-compatible API with key auth (`Authorization: Bearer <key>`).

## Switch ON (use the vLLM lane)

1. Free the whole GPU: `ssh rig 'docker stop llama-swap'`
   (the big LLM lanes are GPU; the embed/rerank lanes are CPU but die with the
   container — OWUI RAG degrades until switch-back. Alternative: evict only
   the loaded GPU models in the llama-swap UI at rig:9292 and leave the
   container up for the CPU lanes.)
2. `ssh rig 'cd /opt/stacks/qwen38-27b-rtx3090 && docker compose --profile single up -d'`
   (prepare re-runs in seconds when the model is already prepared.)
3. Wait for healthy: `docker inspect --format '{{.State.Health.Status}}'
   qwen38-27b-rtx3090-single-1` — first start can take ~10-15 min (JIT caches);
   subsequent starts ~1-2 min.
4. Point the client at `http://192.168.10.12:18020/v1`, model `qwen3.8-27b`,
   key from the vault.
5. **Coverage manifest** (mandate 2): add `qwen38-27b-rtx3090-single-1` to
   `foss-setup/verification/coverage/rig.containers`, commit, and
   `scp` the file to `mini:/opt/verification/coverage/rig.containers` —
   otherwise `containers-manifest-rig` trips.

## Switch OFF (back to llama-swap)

1. `ssh rig 'cd /opt/stacks/qwen38-27b-rtx3090 && docker compose --profile single down'`
2. `ssh rig 'docker start llama-swap'`
3. Remove the manifest line from step ON.5 and redeploy to mini.

## Optional tuning (repo-documented, all in `.env`)

Stock defaults are MTP speculation, 8 slots, 64k ctx (`CTX=fast`), ~120 tok/s.
The repo's "if you are the only user" recommendation, appended to `.env`:

```
SPEC=dflash2
PREFIX_CACHE=1
```

→ ~132-133 tok/s, prefix cache makes turn-2 over a cached document ~40x faster.
`CTX=long` trades some speed for 150k context; `DFLASH_TOKENS=15` is only worth
it when answers quote the prompt (halves slots + 8k ctx). `--profile batch` is
the API-backend mode (~1,000 tok/s aggregate at 64 concurrent) — same GPU
exclusivity. One request at a time is the design point of `single`.

## Verification

- **qwen38-vllm-option-ready** (`checks.d/local-ai.yaml`, daily): asserts the
  option posture — image present, all model artifacts present, and either
  cleanly stopped (default) or running with `/health` OK. Catches model-dir
  rot, image GC, or a half-started server squatting the GPU.
- While it is the active server: `curl -sf http://127.0.0.1:18020/health` and
  one completion; `docker compose run --rm single verify` runs the repo's full
  `verify.sh` (needs the GPU — only while it is the active server).

## Gotchas

- **Never start it while llama-swap has a GPU model loaded** — both want the
  full 24 GB; one of them OOMs. The option-ready check failing with
  `running-unhealthy` usually means exactly this.
- The image is `ghcr.io/syv-ai/qwen38-27b-rtx3090:latest` (prebuilt on every
  upstream commit, patches baked in). Upgrading = `docker compose pull` +
  re-verify; the model dir is untouched by image updates.
- `prepare` downloads from Hugging Face (`dbirks/Qwen3.8-27B-W4A16-AutoRound`,
  ~19.5 GB) — needs outbound internet once. Unauthenticated, so a slow/rate-
  limited link is normal.
- Recreate from scratch: `git clone https://github.com/syv-ai/qwen38-27b-rtx3090
  /opt/stacks/qwen38-27b-rtx3090`, write `.env` (key from the vault),
  `docker compose pull && docker compose run --rm prepare` (CPU, ~30 min on a
  decent link), done — it stays stopped until someone runs `up`.
