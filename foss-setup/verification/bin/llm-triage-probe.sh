#!/usr/bin/env bash
# llm-triage-probe.sh — verify-04 CONSUMER-END probe for the LLM auto-triage layer.
#
# Resolves the SAME endpoint+model as llm-triage.sh (env override in
# /etc/verification/env, else the llama-swap default) and does a REAL chat
# completion. Liveness (`GET /v1/models` -> 200) is NOT enough: the ollama
# :11434 shim answers /models 200 but 404s a big-model completion, which is
# exactly how H24/M19 stayed silent for days. It also guards the reasoning-model
# trap — qwen3.6 spends a small max_tokens budget on <think> and returns EMPTY
# content — by asking for the real triage budget (600) and requiring non-empty
# content back. Prints TRIAGE_LLM_OK / TRIAGE_LLM_FAIL:<reason> to stdout.
set -uo pipefail
ENV_FILE="${VERIFICATION_ENV_FILE:-/etc/verification/env}"
[ -r "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }
# Defaults MUST match llm-triage.sh / llm_triage.py (ai-01, 2026-07-15).
BASE="${LLM_BASE_URL:-http://cachyos.tailb31641.ts.net:9292/v1}"
MODEL="${LLM_MODEL:-qwen3.6-35b-a3b}"
AUTH=(); [ -n "${LLM_API_KEY:-}" ] && AUTH=(-H "Authorization: Bearer ${LLM_API_KEY}")

read -r -d '' BODY <<EOF || true
{"model":"$MODEL","messages":[{"role":"user","content":"Reply with the JSON object {\"ok\":true} and nothing else."}],"temperature":0,"max_tokens":600}
EOF

resp="$(curl -s -m 90 -w $'\n%{http_code}' "${AUTH[@]}" \
        -H 'content-type: application/json' -d "$BODY" \
        "$BASE/chat/completions")" || { echo "TRIAGE_LLM_FAIL:curl_error endpoint=$BASE model=$MODEL"; exit 1; }
code="$(printf '%s' "$resp" | tail -n1)"
json="$(printf '%s' "$resp" | sed '$d')"
if [ "$code" != 200 ]; then
  echo "TRIAGE_LLM_FAIL:http_${code} endpoint=$BASE model=$MODEL"; exit 1
fi
content="$(printf '%s' "$json" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print((d["choices"][0]["message"]["content"] or "").strip())
except Exception:
    print("")
' 2>/dev/null)"
if [ -n "$content" ]; then
  echo "TRIAGE_LLM_OK endpoint=$BASE model=$MODEL"; exit 0
else
  echo "TRIAGE_LLM_FAIL:empty_content endpoint=$BASE model=$MODEL"; exit 1
fi
