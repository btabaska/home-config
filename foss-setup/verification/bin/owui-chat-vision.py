#!/usr/bin/env python3
"""owui-chat-vision.py — CONSUMER-end probe of native vision on the chat-vision lane.

Simulates exactly what the OWUI frontend does for a vision-capable model:
embeds the chat-attached image as an image_url content part and sends it
through OWUI -> LiteLLM -> llama-swap (gemma4-31b-qat-vision + mmproj —
split from the text-only chat lane 2026-08-17; vision is Plant Scout's lane
only, operator decision). The golden asset is the Koehler dandelion botanical
illustration, so the reply (content OR reasoning — gemma thinks first) must
mention one of the obvious words. A text-only regression (mmproj dropped,
capability flag flipped back) fails with the exact "image input is not
supported" 500 the household hit on 2026-08-16.

Env: OWUI_URL, OWUI_API_KEY (required), VISION_MODEL (default chat-vision),
     PLANT_ASSET (default the plant-id golden image).
"""

import base64
import json
import os
import re
import sys
import urllib.request

BASE = os.environ.get("OWUI_URL", "http://192.168.10.12:3000").rstrip("/")
KEY = os.environ["OWUI_API_KEY"]
MODEL = os.environ.get("VISION_MODEL", "chat-vision")
ASSET = os.environ.get(
    "PLANT_ASSET", "/opt/verification/assets/plant-id-dandelion.jpg"
)
MARKERS = re.compile(r"dandelion|taraxacum|flower|botanical|plant", re.I)


def main():
    with open(ASSET, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()

    payload = json.dumps(
        {
            "model": MODEL,
            "stream": False,
            "max_tokens": 2000,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "In one sentence, what is in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64," + b64},
                        },
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
    try:
        with urllib.request.urlopen(req, timeout=280) as resp:
            d = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"CHAT_VISION_FAIL http={e.code} body={e.read()[:200].decode('utf-8','replace')}")
        return 1

    msg = (d.get("choices") or [{}])[0].get("message") or {}
    text = (msg.get("content") or "") + " " + (msg.get("reasoning_content") or "")
    if MARKERS.search(text):
        print(f"CHAT_VISION_OK model={MODEL}")
        return 0
    print(f"CHAT_VISION_FAIL markers absent; head={text.strip()[:200]!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
