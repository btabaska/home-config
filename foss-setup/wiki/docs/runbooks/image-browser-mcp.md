# Image & browser tools (OWUI ComfyUI engine + comfyui-mcp + playwright-mcp)

Runbook for the `image-browser-mcp` verification check and the lai-11 build
(2026-08-06). Three pieces, all on the rig (`local-ai-tooling/docker` compose):

- **OWUI image generation + edit engines = ComfyUI via the gpu-arbiter.**
  Generation: `z_image_turbo_bf16` (8-step turbo, dpmpp_sde/beta, cfg 1,
  default `1024x1024`), node map = the proven `z-image-turbo-realistic` graph.
  Edit: `flux-2-klein-9b-Q8_0` instruction editing (ReferenceLatent, 20 steps,
  cfg 4). Both point at **`http://gpu-arbiter:8189`** — never bare `:8188`.
- **comfyui-mcp** (`:9000/mcp`) — [joenorton/comfyui-mcp-server] v1.1.1, built
  from a pinned git SHA (`docker/comfyui-mcp/Dockerfile`, `COMFYUI_MCP_REF`).
  17 tools; the curated workflow tools `zimage_turbo` + `noobai_anime` come
  from `docker/comfyui-mcp/workflows/*.json` (`PARAM_` placeholders).
- **playwright-mcp** (`:8931/mcp`) — microsoft/playwright-mcp v0.0.79
  (tag@digest pinned), headless chromium, `--isolated`, Host-allowlisted.
  24 tools.

Consumers: OWUI native MCP (filtered: comfyui 3, playwright 8 — see the
[owui-mcp-tools runbook](owui-mcp-tools.md) for the 36-tool budget) and
opencode (both servers full-set via `mcp.playwright`/`mcp.comfyui` in
`local-ai-tooling/opencode.json`, enabled per-agent for build+plan only).

## The rules that bite

- **Everything image goes through the arbiter.** OWUI's engine config, both MCP
  workflows, Marinara and Lumiverse all use `gpu-arbiter:8189`; the arbiter
  unloads llama-swap on `POST /prompt` and `/free`s ComfyUI when the queue
  drains. Pointing anything at `:8188` directly reintroduces the 24 GB VRAM
  OOM class ([rig GPU contention](../architecture/local-ai-build.md)). The
  check FAILs `owui_comfyui_base_not_arbiter` on this drift.
- **OWUI image config is PersistentConfig (DB-only).** Set live via
  `POST /api/v1/images/config/update`; compose env seeds nothing for it. A
  volume wipe reverts the engine to `openai` (disabled) — re-apply per this
  runbook (the node mappings below ARE the rebuild source).
- **OWUI workflow-node mappings need explicit `key`s** (the model's default is
  `text`): gen = model→`2:unet_name`, prompt→`5:text`, width/height→`7`,
  steps/seed→`8`; edit = model→`1:unet_name`, image→`4:image`, prompt→`7:text`,
  width/height→`10,12`, seed→`14:noise_seed`. **Do NOT map `steps` on the edit
  engine** — OWUI's edit path never sends steps, the node renders `None` and
  ComfyUI 400s the whole graph (hit at build).
- **`PARAM_` placeholders in comfyui-mcp workflows:** an *omitted optional*
  param with no server default stays in the graph as the literal string and
  fails validation — curated workflows parameterize ONLY `PARAM_PROMPT` +
  `PARAM_INT_SEED` (seed auto-randomizes server-side).
- **comfyui-mcp binds 127.0.0.1 upstream** — the image build patches the
  `FastMCP` ctor to honor `FASTMCP_HOST=0.0.0.0` (current mcp 1.x SDKs ignore
  the `FASTMCP_*` env). `mcp` is pinned `<2` (SDK-2.0 rename breakage class).
- **playwright-mcp's `--allowed-hosts` entries are `host:port`** — a bare
  hostname/IP entry does NOT match and everything 403s (hit at build). The
  allowlist covers localhost, the compose name, LAN IP, and tailnet name/IP,
  all `:8931`-qualified.
- **Long gens return `status: running`** from comfyui-mcp after ~30 s — poll
  `get_job(prompt_id=…)`; that's protocol, not a failure.

## When `image-browser-mcp` fails

Helper `/opt/verification/bin/image-browser-mcp.py` (repo `verification/bin/`),
one `IMGBROWSER_BAD <reason>` line:

| Reason | Meaning / fix |
|---|---|
| `comfyui_mcp_handshake_failed:*` / `comfyui_tools_list_empty` | container down or it can't reach ComfyUI (it exits if ComfyUI is unreachable at start) → `ssh rig docker logs comfyui-mcp`; check comfyui + gpu-arbiter first. |
| `playwright_mcp_handshake_failed:*` (HTTPError = 403) | container down, or the Host allowlist regressed (`host:port` rule above) → `docker logs playwright-mcp`, fix compose `--allowed-hosts`. |
| `*_owui_connection_missing_or_disabled` / `*_function_filter_empty` | connection deleted/disabled/cleared in OWUI Admin → re-run `local-ai-tooling/scripts/seed-owui-tool-servers.sh` on the rig. |
| `*_filter_entries_match_no_live_tool:<entries>` | upstream renamed/removed tools (image bump?) or a workflow file was renamed → realign the seed-script filter with live `tools/list`. |
| `playwright_navigation_failed_or_marker_missing` | chromium can't launch (container OOM?) or the wiki is down/moved → try the nav by hand (see below), check `wiki.tabaska.us` + mini Caddy. |
| `owui_image_*` / `owui_comfyui_*` | image-engine config drift (UI flip, volume wipe) → re-apply the config per the mappings above; keep the base URL on the arbiter. |

## Hands-on probes

```bash
# MCP handshake + tools (from anywhere on the LAN)
python3 /opt/verification/bin/image-browser-mcp.py   # on the mini, full check

# real generation through OWUI (admin key; ~20 s cold)
curl -s -X POST -H "Authorization: Bearer $OWUI_API_KEY" -H 'Content-Type: application/json' \
  -d '{"prompt":"a red lighthouse at sunset","size":"512x512"}' \
  http://192.168.10.12:3000/api/v1/images/generations

# arbiter take-turns evidence after a gen
ssh rig docker logs gpu-arbiter --since 5m | grep arbiter
#   [arbiter] LLM unloaded before generation
#   [arbiter] ComfyUI freed (queue drained)
```

Build-time evidence (2026-08-06): real 512 px PNG via `/api/v1/images/generations`
(22 s cold, 337 KB), real instruction-edit via `/api/v1/images/edit` (57 s,
night-scene edit of the same lighthouse), real `zimage_turbo` MCP tool gen
(1024 px PNG), real `browser_navigate` to the wiki returning the page title —
all with the arbiter log lines above.

[joenorton/comfyui-mcp-server]: https://github.com/joenorton/comfyui-mcp-server
