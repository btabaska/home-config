# Strata lane — Qwen3.8-Flash-Next on GPU+RAM

**Qwen3.8-Flash-Next** (125B MoE, ~6B active per token, 24,576 experts) running on
the rig's single RTX 3090 Ti + 64 GB RAM through the
[Strata](https://github.com/Niko1221/Strata) engine (MIT). Model =
ISTA-DASLab **GSQ-RCO IQ3_S** (84 GB, Strata's highest-quality size). Public
alias **`strata`** (LiteLLM) / llama-swap model **`strata`**. (lai-31, 2026-10-22.)

## How it fits together

```
OWUI / opencode / ZCode ──► LiteLLM :4000  `strata` alias ─┐   (sends STRATA_API_KEY)
Hermes (Mac) ─────────────► llama-swap :9292 `strata` ◄─────┘
                                 │  shim: start = POST strata:8080/load, stop = POST /unload?wait
                                 ▼
                       strata container (lazy; no VRAM until /load)
                       GPU: 7,330 hot experts (13.9 GiB) + attention/KV/MTP
                       RAM: 36.4 GiB page-locked (experts the GPU does not hold)
                       NVMe: 28.8 GB n-gram table, memory-mapped
```

- **llama-swap owns the card.** `strata` is in the exclusive `big` group, so
  asking for `strata` evicts q38/chat, and asking for q38/chat evicts strata
  (the shim's stop drains the running turn, then unloads). The CPU embed/rerank
  group is untouched, and the gpu-arbiter (ComfyUI) and the Apollo gpu-yield
  unload-all both free it like any other lane.
- **Strata always requires its API key** (`STRATA_API_KEY`, vault
  `ai_stack.strata_api_key`). llama-swap forwards the client's `Authorization`
  header, so: LiteLLM's alias sends it (`os.environ/STRATA_API_KEY`), and Hermes
  sends it (`key_env: STRATA_API_KEY` on the llama-swap custom provider; the
  llama-server lanes ignore the header).
- **One request at a time** (Strata serves one turn; a second waits).

## Measured (2026-10-22, IQ3_S, 128K ctx, int8 KV, MTP on)

| | |
| --- | --- |
| Decode | 120 tok/s (2,000-token coding answer, resident mode); 127 tok/s all-in-RAM mode |
| Prompt read | ~930 tok/s (1.5K prompt) |
| Cold load | 45 s with the files in page cache; ~2 min fully cold (pins 36 GiB) |
| VRAM free while loaded | ~0.9 GiB (`--vram-reserve-mib 1200`) |
| RAM available while loaded | ~16 GB (resident mode) — vs ~6 GB with every expert in RAM |
| Tool calls | OpenAI `tool_calls` well-formed; `reasoning_content` split out |

## Where things live (rig)

- Compose service `strata` in `local-ai-tooling/docker/docker-compose.yml`,
  image `ghcr.io/niko1221/strata:0.2.2-cuda13` **pinned by digest**. Port
  `127.0.0.1:8090` (debug only).
- Data: **`/opt/llm/strata`** — its own btrfs subvolume, deliberately outside the
  snapper root snapshots (a later delete really frees the ~140 GB). Models in
  `Strata-data/models/IQ3_S/`, prepared pack `Strata-data/packs/iq3_s`, draft
  layer `Strata-data/mtp/rt`.
- Run config: `/opt/llm/strata/install/strata-iq3_s.json` — repo copy
  `local-ai-tooling/docker/strata/strata-iq3_s.json` (+ README). Three
  hand-added keys must survive a reinstall: `"lazy_load": true`,
  `--resident-experts`, `--vram-reserve-mib 1200`. **Edit this file with the
  container stopped** — every start regenerates the per-launch
  `state/strata/launch/docker.json` from it; `POST /config` on the live server
  writes only the per-launch file and is lost on restart.
- llama-swap entry `strata` (`docker/llama-swap-config.yaml`), LiteLLM alias
  `strata` (`docker/litellm-config.yaml`), provenance + sha256 in
  `docker/models.manifest.yaml` → `strata:`.

## Clients

| Client | How |
| --- | --- |
| OWUI | model `strata` (open-webui key scope includes it — `scripts/seed-litellm-owui-key-scope.py`) |
| opencode (Mac + rig) | `litellm/strata` (coding-agents key scoped q38/utility/strata) |
| Hermes (Mac) | `-m strata` on provider `custom:192.168.10.12:9292`; `STRATA_API_KEY` in `~/.hermes/.env` |
| ZCode (Mac) | OpenAI-compatible provider, base URL `https://llm.tabaska.us/v1`, key = LiteLLM virtual key `zcode` (vault `ai_stack.litellm_zcode_key`, scoped strata + q38), model `strata` |

## Operate

- Status: `curl -s 127.0.0.1:8090/health` on the rig (`"loaded": true|false`);
  `curl -s localhost:9292/running`.
- Load / unload by hand: request the model, or
  `curl -X POST localhost:9292/api/models/unload/strata`.
- Live monitor: `docker exec -it strata strata monitor` (needs the key:
  `STRATA_API_KEY` from `docker/.env`).
- Engine log (the real failure reasons): `sudo less
  /opt/llm/strata/state/strata/launch/docker.engine.log`.
- Image bump: re-resolve the digest for the new `<ver>-cuda13` tag, edit
  compose, `docker compose up -d strata`; models + pack stay in the subvolume.

## Gotchas

- **Never let it load while another lane holds the card.** First start (not
  lazy yet) died `server_exited` with `cudaMalloc ... weight arena failed (out of
  memory): 63 MiB free` because q38 was resident and Mac clients kept reloading
  it. Lazy + the llama-swap shim is the fix — don't remove `lazy_load`.
- **`/health` 200 ≠ loaded** — read the `loaded` field.
- **Fresh-write data corruption (fix-83 class).** The first download of shard 2
  landed with one 4 KiB block failing its btrfs checksum (`csum failed root 350
  ino 334 off 4378341376`, `corruption_errs` 5→10; reads → EIO). Shard 2 is
  memory-mapped, so a request touching that block can kill the engine. After any
  rig RAM/NVMe incident, re-hash and compare with `models.manifest.yaml`:
  `sudo sha256sum /opt/llm/strata/Strata-data/models/IQ3_S/*.gguf`.
  Replace a bad shard by downloading to a temp name, verifying the sha256 from
  disk (`drop_caches` first), then swapping it in with the container stopped.
- RAM: IQ3_S is Strata's biggest size. With all experts in RAM the box had ~6 GB
  available while loaded; `--resident-experts` is what keeps it livable. If RAM
  pressure returns (new RAM-hungry service), IQ3_XXS is the fallback size
  (`MODEL=IQ3_XXS`, 47 GB shard 1).
- The download-time `Starting Strata ... code 6` with no reason printed was the
  checksum EIO above — read the engine/kernel log, don't just retry.

## Verification

- **strata-lane-posture** (`checks.d/local-ai.yaml`, quick): container up,
  `/health` answers, llama-swap lists the lane, image digest-pinned. Never loads
  the model.
- **strata-e2e** (daily): real completion OWUI-key → LiteLLM → llama-swap shim →
  Strata; helper `local-ai-tooling/scripts/strata-e2e.sh`. If the lane was not
  loaded it unloads it afterwards so the daily probe doesn't hold the card.
