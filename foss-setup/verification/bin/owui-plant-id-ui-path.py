#!/usr/bin/env python3
"""owui-plant-id-ui-path.py — UI-native attach-path probe for identify_plant
(2026-08-17).

The regression this guards: the OWUI 0.11.0 backend reloads saved-chat
messages from the chat DB, injects attached images into content as image_url
PARTS, then strips message["files"] (middleware.py `message.pop("files",
None)`) — all BEFORE tools receive __messages__. A tool that only scans
files/__files__ returns "No attached image found" for every UI chat, while
owui-plant-id-e2e (a raw API caller whose messages pass through untouched,
files key intact) stays green. Exactly that gap broke the household Plant
Scout flow on 2026-08-17 (identify_plant 0.1.0 -> 0.1.1).

Probe: pull the LIVE identify_plant source from the OWUI tools API (= the DB
copy that actually executes — catches seed drift too), run it inside the
open-webui container on the rig with __messages__ shaped exactly like a
post-payload UI chat (image ONLY as an image_url data-URI content part,
__files__ empty), and assert the returned taxa name Taraxacum. Native tool
EXECUTION itself is websocket-side and unprobeable over HTTP
(plant-scout-preset config-gates that); this probes the tool's image
resolution on the UI shape, which is where the household path actually broke.

Env: OWUI_URL (default rig :3000), OWUI_API_KEY (required),
     PLANT_ASSET, RIG_SSH (ssh alias, default rig).
"""

import base64
import json
import os
import shlex
import subprocess
import sys
import urllib.request

BASE = os.environ.get("OWUI_URL", "http://192.168.10.12:3000").rstrip("/")
KEY = os.environ["OWUI_API_KEY"]
ASSET = os.environ.get(
    "PLANT_ASSET", "/opt/verification/assets/plant-id-dandelion.jpg"
)
RIG = os.environ.get("RIG_SSH", "rig")
MARKER = os.environ.get("PLANT_MARKER", "Taraxacum")

DRIVER = r"""
import asyncio, base64, importlib.util, sys, tempfile

blob = sys.stdin.buffer.read()
tool_b64, img_b64 = blob.split(b"\n", 1)
with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as fh:
    fh.write(base64.b64decode(tool_b64))
    tool_path = fh.name
spec = importlib.util.spec_from_file_location("identify_plant_probe", tool_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

uri = "data:image/jpeg;base64," + img_b64.decode()
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "what plant is this"},
            {"type": "image_url", "image_url": {"url": uri}},
        ],
    }
]
out = asyncio.run(
    mod.Tools().identify_plant(rank="species", __messages__=messages, __files__=[])
)
print(out)
"""


def main():
    req = urllib.request.Request(
        f"{BASE}/api/v1/tools/id/identify_plant",
        headers={"Authorization": f"Bearer {KEY}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        tool = json.loads(resp.read())
    content = tool.get("content") or ""
    if "def identify_plant" not in content:
        print("PLANT_UI_PATH_FAIL live tool content missing identify_plant")
        return 1

    with open(ASSET, "rb") as fh:
        img_b64 = base64.b64encode(fh.read())
    payload = base64.b64encode(content.encode()) + b"\n" + img_b64

    # ssh flattens its argv into one remote shell command line, so the driver
    # must be shell-quoted or the remote shell mangles its newlines/quotes.
    remote = f"docker exec -i open-webui python3 -c {shlex.quote(DRIVER)}"
    proc = subprocess.run(
        ["ssh", RIG, remote],
        input=payload,
        capture_output=True,
        timeout=180,
    )
    out = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace")
        print(f"PLANT_UI_PATH_FAIL driver rc={proc.returncode}: {err[-300:]}")
        return 1
    if MARKER.lower() in out.lower():
        print(f"PLANT_UI_PATH_OK marker={MARKER}")
        return 0
    print(f"PLANT_UI_PATH_FAIL marker {MARKER!r} absent; tool said: {out[:300]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
