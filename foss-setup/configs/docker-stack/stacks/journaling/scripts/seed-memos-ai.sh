#!/usr/bin/env bash
# seed-memos-ai.sh (journal-08) — (re-)seed Memos' NATIVE AI integration.
#
# Memos 0.29.1 stores its Settings -> "AI Integrations" + "Transcription" panel in
# the sqlite instance/settings/AI row — no compose file owns it, so a DB
# wipe/restore silently loses the editor audio-recorder's Transcribe button. This
# script idempotently PATCHes the full desired state back:
#
#   provider local-whisper : OPENAI-type -> http://faster-whisper:8000/v1
#                            (container name on the journaling net — Memos calls the
#                            provider SERVER-side, so the container port, not :8010;
#                            Speaches is keyless on the LAN, the key is a dummy)
#   provider rig-litellm   : OPENAI-type -> http://192.168.10.12:4000/v1
#                            (least-priv virtual key, alias `memos`, scoped
#                            chat+utility; canonical vault ai_stack.litellm_memos_key
#                            — pre-wired for future Memos AI features; nothing in
#                            0.29.1 consumes it besides showing as configured)
#   transcription          : provider local-whisper, model Systran/faster-whisper-small,
#                            language en (journal is English; helps the small model)
#
# Usage (on the mini):
#   MEMOS_LLM_KEY=<vault ai_stack.litellm_memos_key> ./scripts/seed-memos-ai.sh
#
# MEMOS_API_TOKEN is read from the stack .env (same PAT n8n uses). Guarded by the
# daily check journaling-memos-native-transcribe (drift-gate + real ai:transcribe).
set -euo pipefail

STACK_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MEMOS_BASE="${MEMOS_BASE:-http://localhost:5230}"
MEMOS_API_TOKEN="${MEMOS_API_TOKEN:-$(grep '^MEMOS_API_TOKEN=' "$STACK_DIR/.env" | cut -d= -f2-)}"
: "${MEMOS_API_TOKEN:?MEMOS_API_TOKEN not in env or $STACK_DIR/.env}"
: "${MEMOS_LLM_KEY:?set MEMOS_LLM_KEY (vault ai_stack.litellm_memos_key)}"

body=$(cat <<JSON
{"name":"instance/settings/AI","aiSetting":{"providers":[
 {"id":"local-whisper","title":"Local Whisper (Speaches on mini)","type":"OPENAI",
  "endpoint":"http://faster-whisper:8000/v1","apiKey":"sk-local-noauth"},
 {"id":"rig-litellm","title":"Rig LiteLLM (chat+utility)","type":"OPENAI",
  "endpoint":"http://192.168.10.12:4000/v1","apiKey":"$MEMOS_LLM_KEY"}
],"transcription":{"providerId":"local-whisper","model":"Systran/faster-whisper-small",
 "language":"en","prompt":""}}}
JSON
)

curl -sf -X PATCH \
  -H "Authorization: Bearer $MEMOS_API_TOKEN" -H "Content-Type: application/json" \
  "$MEMOS_BASE/api/v1/instance/settings/AI" -d "$body" |
  python3 -c '
import json, sys
s = json.load(sys.stdin).get("aiSetting", {})
ids = sorted(p["id"] for p in s.get("providers", []))
tr = s.get("transcription") or {}
ok = ids == ["local-whisper", "rig-litellm"] and tr.get("providerId") == "local-whisper"
print(("SEEDED providers=%s transcription->%s" % (ids, tr.get("model"))) if ok
      else "SEED_FAILED " + json.dumps(s)[:300])
sys.exit(0 if ok else 1)'
