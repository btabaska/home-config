#!/usr/bin/env python3
"""unsloth-studio-e2e.py — CONSUMER-end probe of the Unsloth Studio chain
(2026-08-17).

Chain: Studio API key -> /v1/chat/completions (provider routing) ->
llama_cpp provider "llama-swap (rig lanes)" -> llama-swap -> qwen3.8-27b
lane (ctx 98304, thinking sampler set, reasoning-effort medium — all
server-side in llama-swap-config.yaml) -> asserted marker reply.

This exercises exactly what a laptop client gets at unsloth.tabaska.us:
Studio auth, the saved provider config (DB-only, seeded by local-ai-tooling
scripts/seed-unsloth-studio.py), container-network reachability of
llama-swap, and a real completion on the requested lane. Involves a model
load/swap -> generous timeout.

Also drift-gates the DB config: 1 llama_cpp provider, both scan folders,
and the 4 MCP servers (fleet / comfyui / playwright / memos) must exist.

Env: UNSLOTH_URL (default rig :8210), UNSLOTH_STUDIO_PASSWORD (JWT for the
config gate + provider-id lookup), UNSLOTH_API_KEY (consumer surface),
UNSLOTH_MODEL (default qwen3.8-27b).
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("UNSLOTH_URL", "http://192.168.10.12:8210").rstrip("/")
PW = os.environ["UNSLOTH_STUDIO_PASSWORD"]
APIKEY = os.environ["UNSLOTH_API_KEY"]
MODEL = os.environ.get("UNSLOTH_MODEL", "qwen3.8-27b")
MARKER = "STUDIO-LANE-OK"
EXPECTED_MCP = 4


def call(method, path, data=None, bearer=None, timeout=300):
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(
        BASE + path,
        json.dumps(data).encode() if data is not None else None,
        headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def extract_content(raw):
    try:
        d = json.loads(raw)
        return d["choices"][0]["message"].get("content") or ""
    except Exception:
        pass
    parts = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            line = line[5:].strip()
        if not line or line == "[DONE]":
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        for ch in d.get("choices", []):
            c = (ch.get("delta") or {}).get("content") or (ch.get("message") or {}).get("content")
            if c:
                parts.append(c)
    return "".join(parts)


def main():
    code, raw = call("POST", "/api/auth/login", {"username": "unsloth", "password": PW})
    if code != 200:
        print(f"UNSLOTH_E2E_FAIL login {code}")
        return 1
    jwt = json.loads(raw)["access_token"]

    # config drift gate ------------------------------------------------------
    code, raw = call("GET", "/api/providers/", bearer=jwt)
    providers = json.loads(raw) if code == 200 else []
    llama = [p for p in providers if p.get("provider_type") == "llama_cpp"]
    code, raw = call("GET", "/api/models/scan-folders", bearer=jwt)
    folders = {f["path"] for f in json.loads(raw).get("folders", [])} if code == 200 else set()
    code, raw = call("GET", "/api/mcp/servers/", bearer=jwt)
    mcp = json.loads(raw) if code == 200 else []
    mcp = mcp if isinstance(mcp, list) else mcp.get("servers", [])
    problems = []
    if len(llama) != 1:
        problems.append(f"llama_cpp providers={len(llama)}")
    if not {"/models/gguf", "/models/comfyui"} <= folders:
        problems.append(f"scan-folders={sorted(folders)}")
    if len(mcp) < EXPECTED_MCP:
        problems.append(f"mcp-servers={len(mcp)}<{EXPECTED_MCP}")
    if problems:
        print(f"UNSLOTH_E2E_FAIL config drift: {'; '.join(problems)}")
        return 1

    # consumer completion ----------------------------------------------------
    code, raw = call("POST", "/v1/chat/completions", {
        "model": MODEL,
        "external_model": MODEL,
        "provider_id": llama[0]["id"],
        "stream": False,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": f"Reply with exactly: {MARKER}"}],
    }, bearer=APIKEY)
    if code != 200:
        print(f"UNSLOTH_E2E_FAIL completion {code}: {raw[:200]}")
        return 1
    content = extract_content(raw)
    if MARKER not in content:
        print(f"UNSLOTH_E2E_FAIL marker absent; reply head: {content[:200]}")
        return 1
    print(f"UNSLOTH_E2E_OK model={MODEL} mcp={len(mcp)} folders={len(folders)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
