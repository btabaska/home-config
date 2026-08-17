#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""journaling-memos-mcp (journal-09) — consumer-end probe for the Memos MCP lane.

Memos' BUILT-IN MCP server (/mcp, in Memos since 0.27) is wired as an agent
tool surface: OWUI chat holds a native type-"mcp" connection (id ``memos``,
bearer PAT, filtered to 7 of 19 — search/get/list memos, list_tags,
list_memo_comments, create_memo, update_memo; widened for note-taking
2026-08-17, budget 34/40), and opencode (rig+Mac) speaks to the same endpoint with the full
tool set via {env:MEMOS_MCP_TOKEN}. Canonical wiring: local-ai-tooling
``scripts/seed-owui-tool-servers.sh`` + ``clients/opencode.json``; PAT canonical
at vault journaling.memos.mcp_token (a SEPARATE PAT from n8n's api_token — it
is revocable on its own).

Silent-failure modes this catches, while every container stays green:
  - the PAT is revoked/rotated without the consumers following (handshake 401s);
  - an OWUI volume wipe or Settings edit drops/disables the connection or
    clears the key/filter (PersistentConfig is DB-only);
  - a Memos upgrade renames/removes the chat tools (0.30 replaced the
    whole MCP implementation once already — tools/list is asserted, not
    assumed).

Two stages, both against real consumer surfaces:
  1. A REAL MCP conversation (initialize -> notifications/initialized ->
     tools/list) against the mini's /mcp with the MCP PAT — the exact protocol
     exchange OWUI's MCPClient and opencode run — asserting serverInfo.name
     "Memos" and that all seven chat tools exist in tools/list.
  2. OWUI admin config: the ``memos`` connection is present, type "mcp",
     enabled, auth_type bearer with a non-empty key, URL on :5230/mcp, and the
     function filter is EXACTLY the seven chat tools (drift in either
     direction — lost tools or an unfiltered 19-tool dump into the 40-cap
     budget — fails).

The visible-tool budget itself is owui-mcp-tools' job; opencode's config file
is owned by the local-ai-tooling repo (ai-tooling-clean-pushed tripwire).

Reads MEMOS_MCP_TOKEN + OWUI_URL + OWUI_API_KEY from the runner env
(/etc/verification/env). Prints MEMOS_MCP_OK / MEMOS_MCP_BAD <reason>.
expect ^MEMOS_MCP_OK$.  task_id: journal-09
"""
import json
import os
import sys
import urllib.request

MEMOS_MCP_URL = os.environ.get("MEMOS_MCP_URL", "http://localhost:5230/mcp")
MCP_TOK = os.environ.get("MEMOS_MCP_TOKEN", "")
OWUI_URL = os.environ.get("OWUI_URL", "http://192.168.10.12:3000").rstrip("/")
OWUI_API_KEY = os.environ.get("OWUI_API_KEY", "")
CHAT_TOOLS = {"search_memos", "create_memo", "get_memo", "list_tags",
              "list_memos", "list_memo_comments", "update_memo"}


def bad(reason):
    print("MEMOS_MCP_BAD " + reason)
    sys.exit(0)  # classification via expect-mismatch, not exit code


def post(url, body, headers, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.headers, resp.read().decode("utf-8", "replace")


def sse_result(text):
    if text.lstrip().startswith("{"):
        return json.loads(text)
    for line in text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    raise ValueError("no data: line in MCP response")


def main():
    if not MCP_TOK:
        bad("MEMOS_MCP_TOKEN_unset_in_runner_env")
    if not OWUI_API_KEY:
        bad("no_OWUI_API_KEY_in_runner_env")

    # -- 1. real MCP handshake with the MCP PAT --------------------------------
    h = {"Accept": "application/json, text/event-stream",
         "Authorization": "Bearer " + MCP_TOK,
         "Content-Type": "application/json"}
    try:
        hdrs, body = post(MEMOS_MCP_URL, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "journaling-memos-mcp-check", "version": "1.0"}},
        }, h)
        sess = hdrs.get("mcp-session-id")
        server = sse_result(body).get("result", {}).get("serverInfo", {}).get("name", "")
        if server != "Memos":
            bad(f"handshake_serverInfo={server or 'missing'}")
        hs = dict(h)
        if sess:
            hs["mcp-session-id"] = sess
        post(MEMOS_MCP_URL, {"jsonrpc": "2.0", "method": "notifications/initialized"}, hs)
        _, body = post(MEMOS_MCP_URL, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, hs)
        names = {t["name"] for t in sse_result(body).get("result", {}).get("tools", [])}
    except Exception as e:  # noqa: BLE001 — any failure here is the finding
        bad(f"mcp_handshake_failed:{type(e).__name__}")
    missing = CHAT_TOOLS - names
    if missing:
        bad("chat_tools_missing:" + ",".join(sorted(missing)))

    # -- 2. OWUI connection drift gate ----------------------------------------
    try:
        req = urllib.request.Request(OWUI_URL + "/api/v1/configs/tool_servers",
                                     headers={"Authorization": "Bearer " + OWUI_API_KEY})
        conns = json.load(urllib.request.urlopen(req, timeout=15)).get("TOOL_SERVER_CONNECTIONS") or []
    except Exception as e:  # noqa: BLE001
        bad(f"owui_config_unreachable:{type(e).__name__}")
    memos = next((c for c in conns if (c.get("info") or {}).get("id") == "memos"), None)
    if not memos:
        bad("owui_memos_connection_missing")
    cfg = memos.get("config") or {}
    if memos.get("type") != "mcp" or not cfg.get("enable"):
        bad("owui_memos_connection_wrong_type_or_disabled")
    if ":5230/mcp" not in memos.get("url", ""):
        bad(f"owui_memos_url_drift:{memos.get('url', '')}")
    if memos.get("auth_type") != "bearer" or not memos.get("key"):
        bad("owui_memos_bearer_key_missing")
    raw = cfg.get("function_name_filter_list", "")
    entries = {e.strip() for e in raw.split(",") if e.strip()} if isinstance(raw, str) else {e for e in raw if e}
    if entries != CHAT_TOOLS:
        bad("owui_memos_filter_drift:" + (",".join(sorted(entries)) or "empty"))

    print("MEMOS_MCP_OK")


if __name__ == "__main__":
    main()
