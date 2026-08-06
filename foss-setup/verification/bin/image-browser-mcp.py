#!/usr/bin/env python3
"""image-browser-mcp.py — CONSUMER-END probe for the lai-11 image/browser tool stack.

lai-11 added two streamable-HTTP MCP servers to the rig AI compose
(local-ai-tooling docker/docker-compose.yml) and wired OWUI's image pipeline:
  - comfyui-mcp    (rig :9000/mcp) — joenorton/comfyui-mcp-server v1.1.1 built
    from a pinned git SHA; talks to ComfyUI through the gpu-arbiter (:8189) so
    image gen keeps the take-turns GPU protocol. Curated workflow tools
    zimage_turbo + noobai_anime (docker/comfyui-mcp/workflows).
  - playwright-mcp (rig :8931/mcp) — microsoft/playwright-mcp v0.0.79
    (tag@digest pinned), headless chromium, --isolated, Host-allowlisted.
  - OWUI image generation AND image edit engines = comfyui via the gpu-arbiter
    (PersistentConfig, DB-only — set via the admin API; compose env seeds
    nothing here, and a volume wipe silently reverts the engine to "openai").

What it proves (from the mini, over the LAN — deliberately NO GPU call; the
image-config gate plus the one-time live gen at build time is the GPU
evidence, and comfyui-mcp's tools/list only works when it can reach ComfyUI):
  1. REAL MCP handshakes (initialize -> initialized -> tools/list) against BOTH
     servers — the exact conversation OWUI's MCPClient and opencode run.
  2. OWUI still has both native-mcp connections registered + enabled and every
     function-filter entry matches at least one LIVE tool name (endswith
     semantics, OWUI is_string_allowed) — catches filter/tool-rename drift in
     both directions. (Budget counting lives in the sibling owui-mcp-tools.)
  3. A REAL browser navigation through playwright-mcp: browser_navigate to the
     internal wiki must come back with the page title — proves chromium
     actually launches and renders, not just that the MCP port answers.
     CPU-only, all-LAN.
  4. OWUI image-config drift gate: generation enabled, engine comfyui, base URL
     the gpu-arbiter (:8189, NOT bare ComfyUI :8188 — bypassing the arbiter
     reintroduces the 24GB VRAM OOM class), z-image model + non-empty node
     mapping; same for the edit engine (flux-2-klein via the arbiter).

Prints exactly one classification line on stdout (runner matches ``expect``):
  IMGBROWSER_OK comfy=17 pw=24 nav=ok imgcfg=ok    -> PASS
  IMGBROWSER_BAD <reason>                          -> FAIL

Runs on the mini runner (/etc/verification/env provides OWUI_URL + OWUI_API_KEY).
Diagnostics to stderr; only the final token line to stdout.
"""
import json
import os
import sys
import urllib.error
import urllib.request

COMFY_MCP_URL = os.environ.get("COMFY_MCP_URL", "http://192.168.10.12:9000/mcp")
PW_MCP_URL = os.environ.get("PW_MCP_URL", "http://192.168.10.12:8931/mcp")
OWUI_URL = os.environ.get("OWUI_URL", "http://192.168.10.12:3000").rstrip("/")
OWUI_API_KEY = os.environ.get("OWUI_API_KEY", "")
WIKI_URL = os.environ.get("WIKI_PROBE_URL", "https://wiki.tabaska.us/")
WIKI_MARKER = "Going Analogue"
ARBITER_BASE = "http://gpu-arbiter:8189"


def bad(reason: str) -> None:
    print(f"IMGBROWSER_BAD {reason}")
    sys.exit(0)  # classification is via expect-mismatch, not exit code


def http(method, url, body=None, headers=None, timeout=30):
    req = urllib.request.Request(url, method=method, data=(json.dumps(body).encode() if body is not None else None))
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.headers, resp.read().decode("utf-8", "replace")


def sse_result(text: str):
    """Extract the last JSON-RPC message from an SSE (or plain JSON) MCP response."""
    if text.lstrip().startswith("{"):
        return json.loads(text)
    out = None
    for line in text.splitlines():
        if line.startswith("data:"):
            out = json.loads(line[5:].strip())
    if out is None:
        raise ValueError("no data: line in MCP response")
    return out


MCP_ACCEPT = {"Accept": "application/json, text/event-stream"}


class McpSession:
    """Minimal streamable-HTTP MCP client (what OWUI's MCPClient does per chat)."""

    def __init__(self, url, name):
        self.url, self.name, self.session = url, name, None

    def open(self):
        init = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "image-browser-mcp-check", "version": "1.0"}},
        }
        hdrs, body = http("POST", self.url, init, MCP_ACCEPT)
        self.session = hdrs.get("mcp-session-id")
        server = sse_result(body).get("result", {}).get("serverInfo", {}).get("name", "")
        http("POST", self.url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, self._h())
        return server

    def _h(self):
        h = dict(MCP_ACCEPT)
        if self.session:
            h["mcp-session-id"] = self.session
        return h

    def tools(self):
        _, body = http("POST", self.url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, self._h())
        return [t["name"] for t in sse_result(body).get("result", {}).get("tools", [])]

    def call(self, tool, args, timeout=90):
        _, body = http("POST", self.url,
                       {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": tool, "arguments": args}}, self._h(), timeout=timeout)
        return sse_result(body)

    def close(self):
        if self.session:
            try:
                http("DELETE", self.url, None, {"mcp-session-id": self.session}, timeout=10)
            except Exception:
                pass


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

    # -- 1. handshakes + live tool lists ---------------------------------------------
    live_tools = {}
    sessions = {}
    for key, url, want in (("comfyui", COMFY_MCP_URL, "ComfyUI_MCP_Server"), ("playwright", PW_MCP_URL, "Playwright")):
        s = McpSession(url, key)
        try:
            server = s.open()
            if want.lower() not in server.lower():
                bad(f"{key}_handshake_serverInfo={server or 'missing'}")
            live_tools[key] = s.tools()
            if not live_tools[key]:
                bad(f"{key}_tools_list_empty")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError, KeyError) as e:
            bad(f"{key}_mcp_handshake_failed:{type(e).__name__}")
        sessions[key] = s
    print(f"live tools: comfyui={len(live_tools['comfyui'])} playwright={len(live_tools['playwright'])}", file=sys.stderr)

    auth = {"Authorization": f"Bearer {OWUI_API_KEY}"}
    try:
        # -- 2. OWUI connections registered + filters match live tools ----------------
        try:
            _, body = http("GET", f"{OWUI_URL}/api/v1/configs/tool_servers", None, auth)
            connections = json.loads(body).get("TOOL_SERVER_CONNECTIONS") or []
        except (urllib.error.URLError, OSError, ValueError) as e:
            bad(f"owui_config_unreachable:{type(e).__name__}")
        mcp_conns = {(c.get("info") or {}).get("id"): c for c in connections if c.get("type") == "mcp"}
        for key in ("comfyui", "playwright"):
            c = mcp_conns.get(key)
            if not c or not (c.get("config") or {}).get("enable"):
                bad(f"{key}_owui_connection_missing_or_disabled")
            raw = (c.get("config") or {}).get("function_name_filter_list", "")
            entries = [e.strip() for e in raw.split(",") if e.strip()] if isinstance(raw, str) else list(raw)
            if not entries:
                bad(f"{key}_function_filter_empty")
            visible = [n for n in live_tools[key] if is_allowed(n, entries)]
            # every allow entry must still match a live tool (catches upstream renames)
            stale = [e for e in entries if not e.startswith("!") and not any(n.endswith(e) for n in live_tools[key])]
            if stale:
                bad(f"{key}_filter_entries_match_no_live_tool:{','.join(stale)}")
            print(f"owui {key}: {len(visible)}/{len(live_tools[key])} visible", file=sys.stderr)

        # -- 3. REAL browser navigation to the internal wiki --------------------------
        try:
            r = sessions["playwright"].call("browser_navigate", {"url": WIKI_URL}, timeout=90)
            content = "".join(c.get("text", "") for c in r.get("result", {}).get("content", []))
            if r.get("result", {}).get("isError") or WIKI_MARKER not in content:
                bad(f"playwright_navigation_failed_or_marker_missing:{content[:120]!r}")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError, KeyError) as e:
            bad(f"playwright_navigate_error:{type(e).__name__}")
    finally:
        for s in sessions.values():
            s.close()

    # -- 4. OWUI image gen/edit config drift gate --------------------------------------
    try:
        _, body = http("GET", f"{OWUI_URL}/api/v1/images/config", None, auth)
        icfg = json.loads(body)
    except (urllib.error.URLError, OSError, ValueError) as e:
        bad(f"owui_images_config_unreachable:{type(e).__name__}")
    if not icfg.get("ENABLE_IMAGE_GENERATION"):
        bad("owui_image_generation_disabled")
    if icfg.get("IMAGE_GENERATION_ENGINE") != "comfyui":
        bad(f"owui_image_engine_drift:{icfg.get('IMAGE_GENERATION_ENGINE')}")
    if icfg.get("COMFYUI_BASE_URL") != ARBITER_BASE:
        bad(f"owui_comfyui_base_not_arbiter:{icfg.get('COMFYUI_BASE_URL')}")
    if "z_image" not in (icfg.get("IMAGE_GENERATION_MODEL") or ""):
        bad(f"owui_image_model_drift:{icfg.get('IMAGE_GENERATION_MODEL')}")
    if not icfg.get("COMFYUI_WORKFLOW_NODES"):
        bad("owui_comfyui_workflow_nodes_empty")
    if not icfg.get("ENABLE_IMAGE_EDIT"):
        bad("owui_image_edit_disabled")
    if icfg.get("IMAGE_EDIT_ENGINE") != "comfyui" or icfg.get("IMAGES_EDIT_COMFYUI_BASE_URL") != ARBITER_BASE:
        bad(f"owui_image_edit_drift:{icfg.get('IMAGE_EDIT_ENGINE')}@{icfg.get('IMAGES_EDIT_COMFYUI_BASE_URL')}")

    print(f"IMGBROWSER_OK comfy={len(live_tools['comfyui'])} pw={len(live_tools['playwright'])} nav=ok imgcfg=ok")


if __name__ == "__main__":
    main()
