#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""journaling-memos-native-transcribe (journal-08) — consumer-end probe.

Memos 0.29.1's native AI integration (Settings -> AI Integrations + Transcription)
lives ONLY in the Memos sqlite (instance/settings/AI) — no compose file owns it, so
a DB wipe/restore or a UI edit silently kills the editor's audio-recorder Transcribe
button while every container stays green. Re-seed with the stack's
scripts/seed-memos-ai.sh.

Two stages, both against the real consumer surface:
  1. Drift gate — GET /api/v1/instance/settings/AI must still hold the
     `local-whisper` provider (endpoint http://faster-whisper:8000/v1, key set) with
     transcription wired to it (model Systran/faster-whisper-small), plus the
     `rig-litellm` provider (http://192.168.10.12:4000/v1, key set — vault
     ai_stack.litellm_memos_key) pre-wired for future Memos AI features.
  2. Real transcription — POST the bundled 1 s probe WAV (the same asset
     journaling-whisper-transcribes uses) through Memos' own
     /api/v1/ai:transcribe and require non-empty text. This exercises the full
     chain the Transcribe button uses: memos server -> speaches container ->
     model, not just that the setting row exists.

Reads MEMOS_API_TOKEN from the runner env (/etc/verification/env). Prints
MEMOS_TRANSCRIBE_OK / MEMOS_AI_DRIFT <why> / MEMOS_TRANSCRIBE_EMPTY / ..._ERR.
expect ^MEMOS_TRANSCRIBE_OK$.  task_id: journal-08
"""
import base64
import json
import os
import sys
import urllib.request

MEMOS = os.environ.get("MEMOS_BASE", "http://localhost:5230")
TOK = os.environ.get("MEMOS_API_TOKEN", "")
WAV = os.environ.get(
    "MEMOS_TRANSCRIBE_PROBE", "/opt/verification/assets/whisper-probe.wav"
)
WHISPER_EP = "http://faster-whisper:8000/v1"
LITELLM_EP = "http://192.168.10.12:4000/v1"
MODEL = "Systran/faster-whisper-small"


def call(path, body=None, timeout=120):
    req = urllib.request.Request(
        MEMOS + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": "Bearer " + TOK,
            "Content-Type": "application/json",
        },
    )
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def main():
    if not TOK:
        print("MEMOS_TRANSCRIBE_ERR MEMOS_API_TOKEN unset")
        sys.exit(1)

    ai = call("/api/v1/instance/settings/AI", timeout=15).get("aiSetting") or {}
    providers = {p.get("id"): p for p in ai.get("providers") or []}
    tr = ai.get("transcription") or {}
    lw, ll = providers.get("local-whisper"), providers.get("rig-litellm")
    drift = []
    if not (lw and lw.get("endpoint") == WHISPER_EP and lw.get("apiKeySet")):
        drift.append("local-whisper=%s" % json.dumps(lw))
    if not (ll and ll.get("endpoint") == LITELLM_EP and ll.get("apiKeySet")):
        drift.append("rig-litellm=%s" % json.dumps(ll))
    if not (tr.get("providerId") == "local-whisper" and tr.get("model") == MODEL):
        drift.append("transcription=%s" % json.dumps(tr))
    if drift:
        print("MEMOS_AI_DRIFT " + " ".join(drift)[:300])
        return

    with open(WAV, "rb") as f:
        audio = f.read()
    resp = call(
        "/api/v1/ai:transcribe",
        {
            "audio": {
                "content": base64.b64encode(audio).decode(),
                "filename": os.path.basename(WAV),
                "contentType": "audio/wav",
            }
        },
    )
    text = (resp.get("text") or "").strip()
    print("MEMOS_TRANSCRIBE_OK" if text else "MEMOS_TRANSCRIBE_EMPTY " + json.dumps(resp)[:200])


if __name__ == "__main__":
    main()
