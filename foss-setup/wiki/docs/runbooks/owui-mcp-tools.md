# Open WebUI native MCP tools (fleet-mcp / context7 / mcpo split)

Runbook for the `owui-mcp-tools` verification check and the lai-04 MCP rewire.
OWUI (`0.10.2`, `open-webui` container on the rig, local-ai-tooling compose,
`ai.tabaska.us` → rig `:3000`) consumes tools through two transports:

- **Native MCP (type `mcp`, streamable-HTTP only — OWUI ≥0.6.31):**
    - **fleet** → `http://host.docker.internal:8765/mcp` — the read-only
      fleet-inspection server (`fleet-mcp.service` on the rig host, canonical
      source `local-ai-tooling/ops/fleet-mcp.service`, ai-01).
    - **context7** → `https://mcp.context7.com/mcp` — hosted, keyless (low rate).
- **mcpo OpenAPI bridge (stdio-only servers stay here):** `time`, `fetch`,
  `serena`, `sequential-thinking` at `http://mcpo:8000/<name>`. mcpo *also* still
  serves `/fleet` and `/context7` passthroughs for non-OWUI consumers
  (`mcpo-config.json` unchanged) — OWUI just no longer uses them.

## The rules that bite

- **PersistentConfig, DB-only:** the tool-server connection list lives ONLY in the
  `open_webui_data` volume (config key `tool_server.connections`) — no compose env
  seeds it. A volume wipe silently erases the whole wiring. **Canonical source /
  rebuild:** `local-ai-tooling/scripts/seed-owui-tool-servers.sh` (run on the rig
  with `OWUI_API_KEY` = vault `ai_stack.openwebui_rag_sync_api_key`).
- **Stable server ids matter:** chat models reference servers in
  `model.meta.toolIds` as `server:<id>` (OpenAPI) / `server:mcp:<id>` (MCP) —
  lai-04 set explicit ids (`time`, `fetch`, `serena`, `sequential-thinking`,
  `fleet`, `context7`) and migrated all bound models off the old positional
  `server:0..5` ids. Renaming an id orphans every model binding to it.
- **Function filter (the tool-budget knob):** per-server
  `config.function_name_filter_list` (comma list; `!` prefix = block; matching is
  *endswith*, OWUI `is_string_allowed`). fleet exposes **9/10** tools —
  `run_verification_checks` is filtered out (a minutes-long full check sweep;
  chat-hostile). **Trap:** for openapi/mcpo connections the filter applies to the
  OpenAPI **operationIds** (`tool_<name>_post`), not the bare tool names — a
  bare-name filter silently hides *everything* (the helper FAILs
  `mcpo_filter_matches_zero_tools` on that). Native-mcp filters use bare names.
  Total OWUI-visible budget after the lai-11 rebalance: **36** = fleet 9 +
  context7 2 + serena 10 (read-only intel subset; the 11 mutating tools are
  opencode-only) + time 2 + fetch 1 + sequential-thinking 1 + comfyui 3
  (zimage_turbo/noobai_anime/view_image) + playwright 8 (browse/interact
  subset), cap ≤ 40 — small local models misroute as the tool catalog grows.
  Local native-mcp connections MUST carry a non-empty filter (budget policy,
  enforced); the lai-11 servers' live handshakes + filter validity are the
  sibling `image-browser-mcp` check's job.
- **mcpo `uvx` pinning:** `mcp-server-time` + `mcp-server-fetch` pin `--with mcp<2`
  in `mcpo-config.json`. MCP python SDK 2.0 renamed `McpError` → `MCPError`; with
  unpinned resolution both bridges crashed at the 2026-08-03 reboot and mcpo
  *mounted them anyway with zero tools* (green-but-broken: `openapi.json` served,
  `paths: {}`).
- **API tool-call gotcha:** bare `POST /api/chat/completions` (with `tool_ids`)
  returns the model's raw `tool_calls` **without executing them** — OWUI's native
  execution loop only runs in the full chat pipeline (request carries `chat_id` +
  message `id` + `session_id`; results land in the chat DB under the message's
  `output` items, `content` may stay empty mid-flight).

## When `owui-mcp-tools` fails

The helper is `/opt/verification/bin/owui-mcp-tools.py` (repo
`verification/bin/`); it prints one `OWUI_MCP_BAD <reason>` line:

| Reason | Meaning / fix |
|---|---|
| `fleet_mcp_handshake_failed:*` / `handshake_serverInfo=*` | fleet-mcp down or not speaking MCP → `ssh rig systemctl status fleet-mcp`, `journalctl -u fleet-mcp -n 50`. Restart it; unit is rig-host systemd, not compose. |
| `fleet_tools_list_empty` | server up but no tools registered — check `ops/fleet_mcp.py` on the rig checkout matches the repo. |
| `*_connection_missing_or_disabled` / `fleet_mcp_url_drift` | someone deleted/disabled/edited the connection in Admin → Settings → External Tools → re-run `seed-owui-tool-servers.sh`. |
| `fleet_function_filter_empty_all_tools_exposed` | filter cleared in the UI → re-run the seed script (budget guard is gone until then). |
| `mcpo_bridge_zero_tools:<id>` | that stdio server crashed at mcpo boot (the SDK-2.0 mode) → `docker logs mcpo` for the import traceback, fix/pin in `mcpo-config.json`, `docker restart mcpo`. |
| `mcpo_openapi_unreachable:<id>` | mcpo itself down / port 8000 blocked from the mini. |
| `mcpo_filter_matches_zero_tools:<id>` | the connection's filter entries match no live operationId (bare-name-vs-`tool_*_post` trap, or an upstream rename) → fix the filter in the seed script and re-run it. |
| `mcp_conn_unfiltered:<id>` | a local native-mcp connection (not fleet/context7) has an empty function filter — budget policy says every local mcp server ships a curated allow-list → add one in the seed script. |
| `tool_budget_exceeded total=N` | someone added servers/tools past the cap → trim with per-server `function_name_filter_list` (Admin UI or seed script), keep ≤ 40. |

Consumer-end sanity (what lai-04 proved live): a chat on `coder` with
`tool_ids: ["server:mcp:fleet"]` executed `fleet_list_hosts` over native
streamable-HTTP (fleet-mcp journal logs `CallToolRequest`) and answered with the
real host list.
