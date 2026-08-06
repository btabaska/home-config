# Open WebUI web search + hybrid RAG (SearXNG / qwen3-reranker)

Runbook for the `owui-agentic-search` verification check and the lai-03 Open WebUI
search + RAG quality pass. OWUI (`0.10.2`, `open-webui` container on the rig,
local-ai-tooling compose, `ai.tabaska.us` → rig `:3000`) now searches through the
mini's private SearXNG and reranks hybrid RAG retrieval through the rig's local
qwen3-reranker (lai-01/lai-02).

- **PersistentConfig rule (the thing that bites):** after first boot **the OWUI DB
  wins over env vars**. The compose `environment:` block only *seeds* a fresh
  `open_webui_data` volume. Every toggle below was applied to the **live** install
  via the admin REST API and *also* mirrored as compose env seeds (rebuild parity)
  in local-ai-tooling `docker/docker-compose.yml` — keep both in sync.
- **Admin API auth:** Bearer key at vault `ai_stack.openwebui_rag_sync_api_key`
  (same key the wiki RAG sync and journaling checks use; on the mini runner it is
  `OWUI_API_KEY` + `OWUI_URL` in `/etc/verification/env`). Config endpoints:
  `GET/POST /api/v1/retrieval/config[/update]`, `POST /api/v1/retrieval/embedding/update`,
  `GET/POST /api/v1/models/model[/update]?id=…`.

## Exact toggles applied (2026-08-05, all via API — none are UI-only residuals)

Admin UI equivalents in parentheses (Admin Panel → Settings unless noted).

**Web search** (Settings → Web Search):

| Setting (env seed name) | Value |
|---|---|
| `ENABLE_WEB_SEARCH` | `true` |
| `WEB_SEARCH_ENGINE` | `searxng` (was `kagi`; Kagi key kept in DB/vault for rollback) |
| `SEARXNG_QUERY_URL` | `http://192.168.10.2:8888/search?q=<query>` — **no `&format=json` suffix** (OWUI strips it; the mini instance already serves `formats: [html, json]`) |
| `WEB_SEARCH_RESULT_COUNT` | `5` |
| `WEB_SEARCH_CONCURRENT_REQUESTS` | `5` |
| `BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL` | `true` ("Bypass Embedding and Retrieval" — full results into context; the model never says "no results" on large-context models) |

⚠ The old compose seed used `BYPASS_EMBEDDING_AND_RETRIEVAL`, which in 0.10.x is
the **top-level RAG bypass** (would disable all document RAG on a volume rebuild).
lai-03 corrected the seed to the web-search-scoped var; the top-level one stays
`false`.

**Hybrid RAG + external reranker** (Settings → Documents):

| Setting | Value |
|---|---|
| `ENABLE_RAG_HYBRID_SEARCH` | `true` (BM25 weight left at default 0.5) |
| `ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS` | `true` |
| `RAG_TOP_K` | `20` |
| `RAG_TOP_K_RERANKER` | `5` |
| `RAG_RERANKING_ENGINE` | `external` |
| `RAG_RERANKING_MODEL` | `qwen3-reranker` |
| `RAG_EXTERNAL_RERANKER_URL` | `http://llama-swap:8080/v1/rerank` (container-network address; the same endpoint is rig `:9292/v1/rerank` externally — see the [reranker runbook](rerank.md)) |
| `RAG_EXTERNAL_RERANKER_TIMEOUT` | `120` |
| `RAG_RERANKING_BATCH_SIZE` | `32` |

**Text pipeline** (Settings → Documents): `ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER=true`,
`CHUNK_MIN_SIZE_TARGET=300` (merges header-split fragments), chunk size/overlap left
at 1000/100, `RAG_EMBEDDING_BATCH_SIZE=32`. **The embedding model was deliberately
NOT touched** (`embed` via LiteLLM = Qwen3-Embedding-0.6B) — switching it forces a
full re-index of every knowledge collection.

**Per-model capabilities** (Settings → Models → edit): Web Search capability ON +
Function Calling **Native** for `coder`, `code`, `coder-strong`, `chat`.
`chat-creative`, `fast`, `utility` and the journaling-coach preset were deliberately
left untouched (creative/small models; see the SETUP.md note about weak tool-callers).

## How the agentic loop actually works (0.10.x)

With Native FC + Web Search capability, a UI chat with the 🌐 globe on injects
builtin `search_web` + `fetch_url` tools — the **model picks its own queries**,
OWUI executes them against SearXNG and loops the results back. Two gotchas verified
live:

- Builtin tools are only injected for **real socket sessions**. A bare
  `POST /api/chat/completions` (even with `features.web_search`) returns
  `finish_reason: tool_calls` and expects the *caller* to execute the tool —
  the model answering "from training data" over the API is expected, not drift.
- The forced pre-search flow (OWUI searches before the model sees the prompt) only
  runs on models explicitly set to `legacy` function calling.

## The check

`owui-agentic-search` (`verification/checks.d/local-ai.yaml`, warn, **tier: daily**)
probes the consumer end from the mini in two stages: (1) the retrieval config in
the **DB** must still be wired searxng + hybrid + external qwen3-reranker (env
proves nothing — PersistentConfig), then (2) `POST /api/v1/retrieval/process/web/search`
— the exact code path chat search and the `search_web` builtin execute — must
return real loaded pages. No LLM call is involved, so it is GPU-contention-safe;
daily tier because it fans out to live search engines. One retry with a second
query rides out SearXNG engine suspensions (~180 s).

Audit-safe run:

```bash
VERIFICATION_STATE_DIR=$(mktemp -d) /opt/verification/bin/run-checks.sh --no-notify --host local-ai
```

**If it fails `config=DRIFT`:** someone changed the Admin UI settings — re-apply the
table above (API or UI) and re-sync the compose seeds.
**If it fails `loaded=0`:** walk the chain: `searxng-json-probe` (mini SearXNG
returns JSON results) → mini outbound net/DNS → OWUI logs
(`docker logs open-webui | grep -i search`) on the rig.
**Rerank leg failing:** see [rerank.md](rerank.md) (`rerank-spread` guards the
score spread; OWUI-side evidence is `ExternalReranker:predict` lines in the OWUI
log during a knowledge query).

## Manual probes

```bash
# consumer web search through OWUI (5 SearXNG-sourced pages expected):
curl -s -X POST "$OWUI_URL/api/v1/retrieval/process/web/search" \
  -H "Authorization: Bearer $OWUI_API_KEY" -H 'Content-Type: application/json' \
  -d '{"queries":["debian stable release"]}' | python3 -m json.tool | head

# hybrid + rerank against the wiki knowledge collection (watch OWUI logs for
# ExternalReranker:predict):
curl -s -X POST "$OWUI_URL/api/v1/retrieval/query/collection" \
  -H "Authorization: Bearer $OWUI_API_KEY" -H 'Content-Type: application/json' \
  -d '{"collection_names":["<knowledge-id>"],"query":"immich ml gpu window","hybrid":true}'
```

Verified 2026-08-05: search loaded 5/5 pages (debian.org first); hybrid query on
`homelab-wiki` returned the glue-14 ML-window page at rerank score 0.9999 with
`ExternalReranker:predict:model qwen3-reranker` in the log; a session-scoped chat
on `coder` chose its own `search_web` query and answered with post-training facts
(Debian 13.6, 2026-07) — proof the results flowed through.
