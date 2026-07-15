# `wiki-rag-sync.py`

> wiki-rag-sync — keep the Open WebUI "homelab-wiki" knowledge collection

**Path:** `foss-setup/scripts/ai/wiki-rag-sync.py` · **Category:** [ai](index.md) · **Type:** Python

## What it does

```text
wiki-rag-sync — keep the Open WebUI "homelab-wiki" knowledge collection
in sync with the wiki markdown sources (ai-01 RAG pillar).

Runs on the mini (wiki-rag-sync.timer, daily). Flow:
  1. freshen a dedicated clone of the homelab repo (forgejo:home/homelab)
     at /var/lib/verification/wiki-rag-repo (fetch + hard reset to origin/main)
  2. diff wiki/docs/**/*.md against the local state manifest (sha256)
  3. upload new/changed files to OWUI (/api/v1/files/), wait for processing
     (chunk + embed via LiteLLM `embed` alias -> llama-swap nomic on the rig),
     then attach to the knowledge collection; remove deleted/stale versions
  4. save the manifest

Env (from /etc/verification/env): OWUI_URL (default https://ai.tabaska.us),
OWUI_API_KEY (created 2026-07-15, admin "rag-sync (ai-01)" key).

Stdlib only (mini has Python 3.10 — no oikb, which needs 3.11+).
```

## See also

- [ai scripts](index.md) · [All scripts](../index.md)
