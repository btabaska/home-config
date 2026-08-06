# Local reranker (llama-swap /v1/rerank on the rig)

Runbook for the `rerank-spread` verification check and the rig's local RAG
reranker (lai-02, local-ai buildout). The reranker is **not a container** — it is
a model entry inside the existing `llama-swap` service on the rig, served as its
own CPU-pinned `llama-server` process.

- **Host:** rig (CachyOS, `192.168.10.12` / `cachyos.tailb31641.ts.net`), inside the
  `llama-swap` container (`:9292`, local-ai-tooling compose)
- **Model:** `qwen3-reranker` = **official ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF**
  (639 MB, sha256-pinned in `docker/models.manifest.yaml`)
- **Config:** local-ai-tooling `docker/llama-swap-config.yaml` (canonical source —
  the repo is dual-remoted, push **both** GitHub + Forgejo)
- **Consumers:** Open WebUI hybrid RAG (`RAG_RERANKING_ENGINE=external` →
  `http://rig:9292/v1/rerank`, lai-03) and the LiteLLM `rerank` alias
  (`POST :4000/rerank`, infinity provider)

## The three load-bearing decisions

1. **Official ggml-org GGUF only.** Community Qwen3-Reranker conversions have a
   broken classification-head wiring: the endpoint stays 200-OK but returns
   **near-zero `relevance_score` for everything** — green-but-broken. If the
   manifest sha256 ever mismatches on a re-fetch, do *not* substitute another
   repo's file.
2. **Separate process from the embedder.** Rank pooling (`--rerank`) cannot share
   a `llama-server` process with `--embeddings --pooling last`, so `qwen3-reranker`
   is its own entry in the llama-swap `embed` group (`swap: false` — both CPU
   models coexist) with `capabilities.reranker: true` (llama-swap v240 schema).
3. **CPU-pinned** (`-ngl 0` + `CUDA_VISIBLE_DEVICES=""`): no new daytime VRAM
   consumers on the 24 GB card (see the GPU-contention policy). Ranking ~20 RAG
   chunks on CPU is seconds, not minutes.

## The check

`rerank-spread` (`verification/checks.d/local-ai.yaml`, warn) probes the consumer
end from the mini over the tailnet: it POSTs a query plus one clearly-relevant and
one clearly-irrelevant document to `/v1/rerank` and asserts a **real score
spread** — relevant ≥ 0.5 *and* (relevant − irrelevant) ≥ 0.4. Scores are
sigmoid-normalized 0..1 (llama.cpp b10015); the healthy baseline measured
2026-08-05 was rel = 0.9945 vs irr = 0.000026. Liveness for the container/models
list is covered separately by `rig-llama-swap*` (`rig.yaml`).

**If it fails with near-zero everywhere:** the model file is a broken conversion —
re-fetch with local-ai-tooling `scripts/fetch-models.sh` (sha256-verifying) and
confirm the source repo is `ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF`.

**If it fails with connection/timeout:** treat as llama-swap health — check
`rig-llama-swap` first, then `docker logs llama-swap` on the rig (look for
`exited prematurely` on the `qwen3-reranker` entry). First call after an idle
unload cold-loads the 639 MB model (seconds); the check timeout (240 s) already
covers that.

Run it in isolation from the mini (audit-safe):

```bash
VERIFICATION_STATE_DIR=$(mktemp -d) /opt/verification/bin/run-checks.sh --no-notify --host local-ai
```

## Manual probe

```bash
curl -s -X POST http://cachyos.tailb31641.ts.net:9292/v1/rerank \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-reranker","query":"How do I restart a systemd service on Linux?",
       "documents":["Use systemctl restart nginx.service to restart the unit.",
                    "My favorite pancake recipe uses two eggs and flour."]}'
```

Expect the first document ≈ 0.99 and the second ≈ 0.0000x. Via the gateway:
`POST https://llm.tabaska.us/rerank` with `"model":"rerank"` and a LiteLLM key.
