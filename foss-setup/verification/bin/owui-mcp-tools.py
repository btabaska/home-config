#!/usr/bin/env python3
"""owui-mcp-tools.py — CONSUMER-END probe for OWUI's native MCP tool wiring (lai-04).

lai-04 rewired Open WebUI's External Tools: fleet-mcp (rig :8765/mcp) and the other
native type-"mcp" streamable-HTTP servers (comfyui/playwright/memos), with the
stdio-only servers (time/fetch/sequential-thinking) bridged through mcpo. Canonical
connection list: local-ai-tooling ``scripts/seed-owui-tool-servers.sh``
(PersistentConfig, DB-only — a volume wipe silently erases it; this check is the
tripwire). 2026-08-17 (journal-09 follow-up): serena (9) + context7 (2) were
REMOVED from OWUI — coding tool-calls are opencode's job (it keeps full serena +
context7 via its own MCP clients) — and memos widened (now 7). 2026-08-20:
fleet grew the read-only filesystem trio (list_dir/find_files/disk_usage),
9 -> 12 visible; designed total 37.

What it proves (from the mini, over the LAN):
  1. The fleet-mcp streamable-HTTP endpoint completes a REAL MCP handshake
     (initialize -> notifications/initialized -> tools/list) — the exact protocol
     conversation OWUI's MCPClient runs per chat, not a liveness ping. A port that
     answers 200 but can't speak MCP (e.g. the pre-lai-04 GET 406 confusion) FAILs.
  2. OWUI's admin API still shows the fleet native-mcp server registered + enabled
     with a non-empty function filter — catches "someone deleted/disabled the
     connection or cleared the filter in the UI".
  3. The TOTAL OWUI-visible tool budget is within cap (<= 40; designed 37 as of
     2026-08-20: fleet 12 + time 2 + fetch 1 + sequential-thinking 1 +
     comfyui 3 + playwright 8 + openzim 3 + memos 7).
     Fleet's exposed count = live tools/list names intersected with the configured
     filter (same endswith allow-list semantics as OWUI's ``is_string_allowed``);
     mcpo/OpenAPI counts come from each bridge's live openapi.json operationIds
     (``tool_<name>_post`` — the names OWUI actually filters/exposes) with the
     per-connection filter applied — so a broken bridge (the 2026-08-03
     mcp-SDK-2.0 breakage mounted time/fetch with ZERO tools) or a filter that
     matches nothing (the operationId-vs-path trap) shows up here. Non-fleet
     native-mcp connections (comfyui/playwright/memos) are counted by their
     allow-list size and MUST
     carry a non-empty filter — budget policy; their live tools/list + filter
     validity is probed by the sibling check ``image-browser-mcp``.

Prints exactly one classification line on stdout (runner matches ``expect``):
  OWUI_MCP_OK fleet=12 mcp_other=18 mcpo=7 total=37   all good        -> PASS
  OWUI_MCP_BAD <reason>                    handshake/config/budget bad -> FAIL

Runs on the mini runner (``/etc/verification/env`` provides OWUI_URL + OWUI_API_KEY).
Diagnostics to stderr; only the final token line to stdout.
"""
import json
import os
import sys
import urllib.error
import urllib.request

FLEET_MCP_URL = os.environ.get("FLEET_MCP_URL", "http://192.168.10.12:8765/mcp")
OWUI_URL = os.environ.get("OWUI_URL", "http://192.168.10.12:3000").rstrip("/")
OWUI_API_KEY = os.environ.get("OWUI_API_KEY", "")
# mcpo as seen from the mini (OWUI's config stores the container-network name mcpo:8000)
MCPO_LAN = os.environ.get("MCPO_LAN_URL", "http://192.168.10.12:8000").rstrip("/")
BUDGET = 40


def bad(reason: str) -> None:
    print(f"OWUI_MCP_BAD {reason}")
    sys.exit(0)  # classification is via expect-mismatch, not exit code


def http(method, url, body=None, headers=None, timeout=25):
    req = urllib.request.Request(url, method=method, data=(json.dumps(body).encode() if body is not None else None))
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.headers, resp.read().decode("utf-8", "replace")


def sse_result(text: str):
    """Extract the first JSON-RPC result from an SSE (or plain JSON) MCP response."""
    if text.lstrip().startswith("{"):
        return json.loads(text)
    for line in text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    raise ValueError("no data: line in MCP response")


def is_allowed(name: str, filter_entries) -> bool:
    """Mirror OWUI utils.misc.is_string_allowed for a pure allow-list."""
    allow = [e for e in filter_entries if e and not e.startswith("!")]
    block = [e[1:] for e in filter_entries if e and e.startswith("!")]
    if allow and not any(name.endswith(a) for a in allow):
        return False
    if any(name.endswith(b) for b in block):
        return False
    return True


def main() -> None:
    if not OWUI_API_KEY:
        bad("no_OWUI_API_KEY_in_runner_env")

    # -- 1. real MCP handshake against fleet-mcp (what OWUI's MCPClient does) --------
    mcp_headers = {"Accept": "application/json, text/event-stream"}
    session = None
    try:
        init = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "owui-mcp-tools-check", "version": "1.0"}},
        }
        hdrs, body = http("POST", FLEET_MCP_URL, init, mcp_headers)
        session = hdrs.get("mcp-session-id")
        result = sse_result(body).get("result", {})
        server_name = result.get("serverInfo", {}).get("name", "")
        if server_name != "fleet":
            bad(f"handshake_serverInfo={server_name or 'missing'}")
        sess_headers = dict(mcp_headers)
        if session:
            sess_headers["mcp-session-id"] = session
        http("POST", FLEET_MCP_URL, {"jsonrpc": "2.0", "method": "notifications/initialized"}, sess_headers)
        _, body = http("POST", FLEET_MCP_URL, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, sess_headers)
        fleet_tool_names = [t["name"] for t in sse_result(body).get("result", {}).get("tools", [])]
        if not fleet_tool_names:
            bad("fleet_tools_list_empty")
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        bad(f"fleet_mcp_handshake_failed:{type(e).__name__}")
    finally:
        if session:
            try:
                http("DELETE", FLEET_MCP_URL, None, {"mcp-session-id": session}, timeout=10)
            except Exception:
                pass

    # -- 2. OWUI admin config: both native servers registered + enabled -------------
    auth = {"Authorization": f"Bearer {OWUI_API_KEY}"}
    try:
        _, body = http("GET", f"{OWUI_URL}/api/v1/configs/tool_servers", None, auth)
        connections = json.loads(body).get("TOOL_SERVER_CONNECTIONS") or []
    except (urllib.error.URLError, OSError, ValueError) as e:
        bad(f"owui_config_unreachable:{type(e).__name__}")
    mcp_conns = {(c.get("info") or {}).get("id"): c for c in connections if c.get("type") == "mcp"}
    fleet = mcp_conns.get("fleet")
    if not fleet or not (fleet.get("config") or {}).get("enable"):
        bad("fleet_mcp_connection_missing_or_disabled")
    if ":8765/mcp" not in fleet.get("url", ""):
        bad(f"fleet_mcp_url_drift:{fleet.get('url', '')}")
    filter_raw = (fleet.get("config") or {}).get("function_name_filter_list", "")
    filter_entries = [e.strip() for e in filter_raw.split(",") if e.strip()] if isinstance(filter_raw, str) else list(filter_raw)
    if not filter_entries:
        bad("fleet_function_filter_empty_all_tools_exposed")

    # -- 3. total visible-tool budget ------------------------------------------------
    fleet_visible = sum(1 for n in fleet_tool_names if is_allowed(n, filter_entries))
    if fleet_visible == 0:
        bad("fleet_filter_matches_zero_tools")

    def conn_filter(c):
        raw = (c.get("config") or {}).get("function_name_filter_list", "")
        return [e.strip() for e in raw.split(",") if e.strip()] if isinstance(raw, str) else [e for e in raw if e]

    # non-fleet native-mcp connections (comfyui/playwright/memos) count by their
    # allow-list size; an unfiltered mcp connection breaks the budget policy
    # (comfyui/playwright live filter validity is image-browser-mcp's job; memos
    # is journaling-memos-mcp's).
    mcp_other = 0
    for c in connections:
        if c.get("type") != "mcp" or not (c.get("config") or {}).get("enable"):
            continue
        cid = (c.get("info") or {}).get("id", "?")
        if cid == "fleet":
            continue
        entries = [e for e in conn_filter(c) if not e.startswith("!")]
        if not entries:
            bad(f"mcp_conn_unfiltered:{cid}")
        print(f"mcp {cid}: {len(entries)} tools (filter size)", file=sys.stderr)
        mcp_other += len(entries)

    mcpo_total = 0
    for c in connections:
        if c.get("type", "openapi") != "openapi" or not (c.get("config") or {}).get("enable"):
            continue
        url = c.get("url", "").replace("http://mcpo:8000", MCPO_LAN)
        cid = (c.get("info") or {}).get("id", "?")
        try:
            _, body = http("GET", f"{url.rstrip('/')}/{c.get('path', 'openapi.json')}", None, {}, timeout=20)
            paths = json.loads(body).get("paths", {})
        except (urllib.error.URLError, OSError, ValueError) as e:
            bad(f"mcpo_openapi_unreachable:{cid}:{type(e).__name__}")
        # OWUI's visible names are the OpenAPI operationIds (tool_<name>_post),
        # and the per-connection filter applies to THOSE (endswith semantics) —
        # a filter written against bare tool names silently hides everything.
        op_ids = [op.get("operationId") for ops in paths.values() for op in ops.values()
                  if isinstance(op, dict) and op.get("operationId")]
        if not op_ids:
            bad(f"mcpo_bridge_zero_tools:{cid}")
        entries = conn_filter(c)
        n = sum(1 for name in op_ids if is_allowed(name, entries)) if entries else len(op_ids)
        if n == 0:
            bad(f"mcpo_filter_matches_zero_tools:{cid}")
        print(f"openapi {cid}: {n}/{len(op_ids)} tools visible", file=sys.stderr)
        mcpo_total += n

    total = fleet_visible + mcp_other + mcpo_total
    if total > BUDGET:
        bad(f"tool_budget_exceeded total={total} cap={BUDGET}")
    print(f"OWUI_MCP_OK fleet={fleet_visible} mcp_other={mcp_other} mcpo={mcpo_total} total={total}")


if __name__ == "__main__":
    main()
