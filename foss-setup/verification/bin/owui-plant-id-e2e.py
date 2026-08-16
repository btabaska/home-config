#!/usr/bin/env python3
"""owui-plant-id-e2e.py — CONSUMER-end probe of the plant-ID chain (2026-08-16).

Chain: OWUI chat (+attached golden photo) -> identify_plant workspace tool ->
bioclip-api (rig :8199, BioCLIP 2) -> ranked taxa -> LLM narrates.

Golden asset: a Wikimedia Taraxacum officinale (dandelion) image. BioCLIP 2
pins the GENUS unambiguously (top-3 all Taraxacum) while species-level within
Taraxacum microspecies is genuinely ambiguous — so the assert is genus-level.

Probe: upload the asset via /api/v1/files, run a non-streamed chat completion
with tool_ids=["identify_plant"], assert "Taraxacum" appears in the reply.
A model that answers without calling the tool fails the assert — that is
consumer-end signal (the household flow is exactly this call path), same
philosophy as owui-agentic-search stage 2.

Env: OWUI_URL (default rig :3000), OWUI_API_KEY (required),
     PLANT_ASSET, PLANT_MODEL (default gemma).
"""

import json
import os
import sys
import urllib.request
import uuid

BASE = os.environ.get("OWUI_URL", "http://192.168.10.12:3000").rstrip("/")
KEY = os.environ["OWUI_API_KEY"]
ASSET = os.environ.get(
    "PLANT_ASSET", "/opt/verification/assets/plant-id-dandelion.jpg"
)
MODEL = os.environ.get("PLANT_MODEL", "chat")
MARKER = os.environ.get("PLANT_MARKER", "Taraxacum")


def api(path, data=None, content_type="application/json", timeout=180):
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": content_type},
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def upload(path):
    boundary = uuid.uuid4().hex
    with open(path, "rb") as fh:
        img = fh.read()
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"plant-probe.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n"
    ).encode() + img + f"\r\n--{boundary}--\r\n".encode()
    return api(
        "/api/v1/files/",
        data=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )


def main():
    fid = upload(ASSET).get("id")
    if not fid:
        print("PLANT_ID_E2E_FAIL upload returned no file id")
        return 1

    # stream=True + function_calling "legacy" are BOTH required (verified on
    # v0.11.0): native mode only executes tool_calls inside the UI's session
    # loop (session_id) — a raw API call gets the unexecuted tool_calls back.
    # Legacy mode runs chat_completion_tools_handler server-side pre-completion,
    # which is what makes this probe-able. UI chats use native mode and work.
    payload = json.dumps(
        {
            "model": MODEL,
            "stream": True,
            "params": {"function_calling": "legacy"},
            "tool_ids": ["identify_plant"],
            "files": [{"type": "file", "id": fid}],
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "I attached a photo of a plant. Use the identify_plant "
                        "tool to identify it, then tell me the top match with "
                        "its scientific name."
                    ),
                    "files": [
                        {"type": "image", "url": f"/api/v1/files/{fid}/content"}
                    ],
                }
            ],
        }
    ).encode()

    req = urllib.request.Request(
        BASE + "/api/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    chunks = []
    with urllib.request.urlopen(req, timeout=300) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            line = line[5:].strip()
            if line == "[DONE]":
                break
            try:
                delta = json.loads(line)
            except ValueError:
                continue
            for choice in delta.get("choices", []):
                content = (choice.get("delta") or {}).get("content")
                if content:
                    chunks.append(content)
    text = "".join(chunks)
    if MARKER.lower() in text.lower():
        print(f"PLANT_ID_E2E_OK marker={MARKER} model={MODEL}")
        return 0
    print(f"PLANT_ID_E2E_FAIL marker {MARKER!r} absent; reply head: {text[:400]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
