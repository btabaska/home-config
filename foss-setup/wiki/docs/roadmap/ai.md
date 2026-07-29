# Roadmap — ai

9 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `ai-01` | Local-AI buildout: llama.cpp/llama-swap stack, coding + ops agents, wiki RAG | ✅ done | multi-session |
| `ai-02` | Mirror local-ai-tooling to Forgejo (git.tabaska.us) as a second remote | ✅ done | 1 session |
| `ai-03` | Wire local-ai-tooling into the fleet drift / hygiene controls (clean + pushed-to-both tripwire) | ✅ done | 1 session |
| `ai-04` | Vault-map the local-ai-tooling docker/.env bootstrap secrets + .env.example parity | ✅ done | 1 session |
| `ai-05` | Close the service-catalog + wiki gaps for the rig AI services (comfyui, gpu-arbiter, per-service pages) | ⬜ open | 1 session |
| `ai-06` | Model-weight manifest for /opt/llm/models (make the stack rebuildable after disk loss) | ⬜ open | 1 session |
| `ai-07` | Reconcile / retire the stale local-ai-tooling build-handoff docs against live truth | ⬜ open | 1 session |
| `nas-32` | Offload Immich ML (smart search, faces, OCR) to the rig GPU (RTX 3090 Ti, CUDA) | ✅ done | 1 hr |
| `nas-33` | Re-tune Immich duplicate-detection maxDistance for the SigLIP2 embeddings | ✅ done | 20-30 min |

[← Roadmap overview](index.md)
