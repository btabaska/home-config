# Local-AI build — initiative plan (ai-01, expanded)

**Status:** 🔬 scoping — deep research commissioned 2026-07-13, plan to follow.
**Origin:** roadmap prune (#17) — `ai-01` was "optional local-AI extras"; the
operator chose to **keep and expand** it into a first-class initiative, possibly
its own rig plan.

## The vision (operator, 2026-07-13)

> Expand the local-AI stack so that **OpenWebUI + opencode are the best coding
> tools I have** — a full **Claude-like tooling experience matched to the model
> size**: assistants, a good UI, tool use, etc. Give them access to a **skills
> library** I can invoke from spots around the home network — e.g. an **agent
> that diagnoses why a service isn't working**. Invest heavily in the **best
> local-first AI build possible**, grounded in the **state of 2026**, the
> **hardware I have**, and the use case of **local-first AI software development
> and question-answering.**

Two pillars:
1. **Local-first AI software development** — opencode (+ OWUI) as a genuinely
   good coding agent on local models, with Claude-Code-like ergonomics scaled to
   what a 24 GB GPU can run well.
2. **Home-ops / Q&A agents** — a reusable skills library + agents reachable from
   around the LAN (e.g. "why is service X down?", log triage, doc Q&A/RAG).

## Current baseline (live, 2026-07-13)

- **Rig hardware:** RTX 3090 Ti **24 GB VRAM**, i7-12700K (20 threads), **62 GB RAM**,
  CachyOS. The single GPU is shared with game streaming + game servers
  (see task `game-13` GPU-contention policy) and is a **known SPOF** — the
  rig-only AI stack with **no fallback** is an accepted decision
  (see memory `ai-stack-topology`).
- **Live stack (rig, separate `local-ai-tooling` repo):** Ollama (native model
  server) + **LiteLLM** gateway + **Open WebUI** + **mcpo** (MCP↔OpenAPI proxy),
  all in docker except Ollama. `litellm-db` = postgres:16.
- **Not yet:** opencode integration, an agent/skills framework, RAG/knowledge
  base, image-gen (ComfyUI), model selection tuned for 24 GB, and any
  home-network-reachable ops agents.

## Open scope questions (for the deep research to answer, grounded in 2026)

- Best **local coding models** runnable well on 24 GB VRAM (quant, context length,
  tool-calling quality) for agentic SWE; where local realistically lands vs
  frontier, and where to draw the line.
- **opencode** (and alternatives) as the local coding-agent front end: setup
  against LiteLLM/Ollama, tool use, repo awareness, ergonomics vs Claude Code.
- **Agent/skills framework** for reusable, LAN-invocable skills + an ops agent
  that can inspect the fleet (ties into the existing verification harness).
- **RAG / knowledge** stack for home Q&A (docs, runbooks, service state).
- **Serving/throughput**: Ollama vs vLLM vs llama.cpp/TabbyAPI on this GPU;
  concurrency; how to coexist with game streaming (VRAM budget, scheduling).
- **Whether to split into its own rig plan** and how it slots against the
  `local-ai-tooling` repo + this control repo.

## Next step

Deep-research report (2026-grounded) → a concrete, phased build plan lands here,
then it becomes its own tracked workstream. Until then this is scoping only; the
existing OWUI/LiteLLM/Ollama stack keeps running as-is.
