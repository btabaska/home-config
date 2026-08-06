# local-deep-research (iterative deep-research assistant)

Runbook for the `ldr-research-e2e` verification check and general operation of
**local-deep-research (LDR)** — the fleet's tier-2 research tool (lai-08, local-ai
buildout): multi-step search + synthesis with citations, all local (LiteLLM
`coder-strong` + the mini SearXNG). Rig services get no generated service page;
this runbook plus the compose comments are the docs.

- **Host:** rig (`192.168.10.12`), Docker, `local-ai-tooling` stack
  (`~/Documents/GitHub/local-ai-tooling/docker/docker-compose.yml`)
- **URLs:** <https://ldr.tabaska.us> (humans, via the mini Caddy) ·
  `http://192.168.10.12:5000` (LAN — Homepage siteMonitor, verification)
- **Image:** `localdeepresearch/local-deep-research:1.10.1` **pinned by digest**
  (re-resolve + bump to update, like the rest of the AI stack — `ai-images-pinned`
  ignores it only because it scans the five once-rolling services; keep the pin)
- **LLM:** provider `openai_endpoint` → `http://litellm:4000/v1`, model
  **`coder-strong`** (qwen3.6-27b via llama-swap). Key = scoped LiteLLM virtual key
  (`coder-strong`/`fast` only), `.env` `LDR_LITELLM_KEY`, vault `ai_stack.litellm_ldr_key`
- **Search:** `search.tool=searxng` → `http://192.168.10.2:8888` (the lai-01 instance;
  JSON formats enabled server-side — see [SearXNG runbook](searxng.md))
- **State:** named volumes `ldr_data` (per-user encrypted DBs) + `ldr_scripts`

## Auth model (unusual — read before "fixing" login)

Every LDR account gets its **own SQLCipher database encrypted with a key derived
from the password**. There is no admin reset: a lost password = that account's
research history is gone (make a new account). Registration is open (LAN/tailnet
posture, app login is the gate — same stance as Lumiverse). The operator account is
whatever you register in the UI; the dedicated **`ldr-probe`** account (password:
vault `ai_stack.ldr_probe_password`, rig `docker/.env`) belongs to the verification
check — don't use it interactively, and don't worry if it reappears after a volume
wipe (the check re-registers it automatically).

## Config is env-locked (not UI-editable)

The `LDR_*` env vars in the compose are **settings overrides**: a non-empty env var
beats the per-user settings DB on every boot and shows the field locked in the UI.
(Opposite trap to OWUI PersistentConfig, where the DB wins.) So provider/model/search
wiring changes = edit the compose/`.env` in `local-ai-tooling`, `docker compose up -d`,
commit, push **both** remotes. LDR 1.10 has one research model (no strong/fast role
split); the scoped key already allows `fast` if upstream adds one.

## The consumer check

`ldr-research-e2e` (`verification/checks.d/local-ai.yaml`, `tier: daily`, warn) runs
`scripts/ldr-e2e.py` from the rig checkout (repo-canonical; `ai-tooling-clean-pushed`
keeps live==repo). It is a full consumer-chain probe, not liveness:

1. **Best-effort GPU gate** (mirrors `journaling-loop-e2e`): tiny completion against
   llama-swap `qwen3.6-27b` directly. If the strong model can't load (Immich ML night
   window, a game holding VRAM — see the rig GPU-contention policy),
   prints `LDR_E2E_SKIP_GPU_BUSY` = **PASS**, because contention is policy, not an
   incident. Otherwise the model is now warm for step 3.
2. Logs into LDR as `ldr-probe` (auto-re-registers on 401 after a volume wipe).
3. Starts a **real quick-mode research** (1 iteration, SearXNG, coder-strong), polls
   to completion, and requires a **cited report** (>500 chars, ≥3 distinct links).
   Measured healthy: ~100 s warm, `sources=38`.

A real `LDR_E2E_BAD` means the model **was** loadable but the pipeline broke — check
`reason=` in the output: `auth-flow`/`login-failed` (probe creds vs vault),
`start-research`/`research-failed` (LDR ↔ LiteLLM: bad/rotated `LDR_LITELLM_KEY` →
LiteLLM 401; llama-swap OOM mid-run → LiteLLM 500), `report-thin` (research
"completed" but few/no citations — usually SearXNG returning nothing: run the
`searxng-json-probe` check next).

## Troubleshooting

- **Research starts then fails / empty answers.** `docker logs local-deep-research`
  on the rig. LiteLLM 401 = the virtual key was rotated/deleted — re-mint scoped to
  `["coder-strong","fast"]`, update rig `docker/.env` + vault `ai_stack.litellm_ldr_key`,
  `docker compose up -d local-deep-research`. LiteLLM 500 = llama-swap OOM (VRAM
  contention — retry by day; the card is free 07:00–01:00 EDT).
- **Reports have no sources.** LDR → SearXNG path: from the rig,
  `curl 'http://192.168.10.2:8888/search?q=test&format=json'` must return results
  (403 = json format dropped server-side; see the SearXNG runbook).
- **Login page loops / "invalid credentials" for the operator.** Per-user encrypted
  DB — there is no reset; register a fresh account. Only `ldr-probe` is vaulted.
- **Container unhealthy after an image bump.** The settings→env mapping
  (`LDR_LLM_OPENAI_ENDPOINT_API_KEY` etc.) has churned between minor versions —
  re-verify with `docker exec local-deep-research printenv | grep LDR_` and the
  settings API before trusting a bump; keep the digest pin discipline.
- **Volume wipe.** `ldr_data` holds research history only (all config is env-driven);
  after a wipe the check self-heals its probe account and the operator re-registers.
