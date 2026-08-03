#!/usr/bin/env bash
# llm-triage-probe.sh — verify-04 CONSUMER-END probe for the LLM auto-triage layer.
#
# Resolves the SAME endpoint+model+token-budget as llm_triage.py (env override in
# /etc/verification/env, else the llama-swap defaults) and does a REAL triage-shaped
# completion, then requires the reply to PARSE as the strict verdict JSON.
#
# Why this shape (SH17, fix-61, 2026-08-02): the old probe sent a trivial one-line
# question at max_tokens=600 and only required NON-EMPTY content — so it passed
# green for weeks while 91% of REAL verdicts came back empty/malformed (qwen3.6 is
# a reasoning model; 600 tokens were consumed by <think> before any JSON on a
# realistic prompt). This probe now mirrors the real path: a domain skill as the
# system prompt + a synthetic failed-check as the user prompt, at TRIAGE_MAX_TOKENS,
# asserting a valid JSON object with the required keys comes back. That makes it
# structurally able to catch the reasoning-budget/empty-content class it exists for.
# It still guards the earlier traps (endpoint drift, /models-200 shim, retired
# model). Prints TRIAGE_LLM_OK / TRIAGE_LLM_FAIL:<reason> to stdout.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)/skills"
ENV_FILE="${VERIFICATION_ENV_FILE:-/etc/verification/env}"
[ -r "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }
# Defaults MUST match llm-triage.sh / llm_triage.py (ai-01, 2026-07-15; fix-61).
BASE="${LLM_BASE_URL:-http://cachyos.tailb31641.ts.net:9292/v1}"
MODEL="${LLM_MODEL:-qwen3.6-35b-a3b}"
MAX_TOKENS="${TRIAGE_MAX_TOKENS:-4000}"
AUTH=(); [ -n "${LLM_API_KEY:-}" ] && AUTH=(-H "Authorization: Bearer ${LLM_API_KEY}")

SKILL_FILE="${SKILLS_DIR}/docker-triage.md"
[ -r "$SKILL_FILE" ] || { echo "TRIAGE_LLM_FAIL:skill_missing $SKILL_FILE"; exit 1; }

resp="$(SKILL_FILE="$SKILL_FILE" MODEL="$MODEL" MAX_TOKENS="$MAX_TOKENS" BASE="$BASE" \
  python3 - "${AUTH[@]}" <<'PY' 2>/dev/null || true
import json, os, sys, urllib.request
base = os.environ["BASE"]; model = os.environ["MODEL"]
mt = int(os.environ["MAX_TOKENS"]); skill = open(os.environ["SKILL_FILE"]).read()
check = {"id": "triage-probe-synthetic", "name": "synthetic probe check",
         "host": "mini", "cmd": "echo probe", "severity": "warn",
         "task_id": "verify-04", "exit_code": 1, "output": "probe=synthetic-failure"}
user = ("Failed check:\n" + json.dumps(check, indent=2) +
        "\n\nRespond with ONLY one strict JSON object with keys diagnosis, "
        "likely_cause, suggested_fix_commands, confidence, escalate. No markdown.")
body = json.dumps({"model": model, "temperature": 0, "max_tokens": mt,
                   "messages": [{"role": "system", "content": skill},
                                {"role": "user", "content": user}]}).encode()
req = urllib.request.Request(base + "/chat/completions", data=body,
                             headers={"Content-Type": "application/json"})
# argv carries the -H "Authorization: Bearer ..." pair if LLM_API_KEY is set
a = sys.argv[1:]
if len(a) == 2 and a[0] == "-H" and a[1].lower().startswith("authorization:"):
    req.add_header(*[p.strip() for p in a[1].split(":", 1)])
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    print("HTTP 200")
    print(d["choices"][0]["message"]["content"] or "")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}")
except Exception as e:
    print(f"ERR {type(e).__name__}")
PY
)"

status_line="$(printf '%s\n' "$resp" | head -n1)"
content="$(printf '%s\n' "$resp" | tail -n +2)"
case "$status_line" in
  "HTTP 200") : ;;
  "HTTP "*)   echo "TRIAGE_LLM_FAIL:http_${status_line#HTTP } endpoint=$BASE model=$MODEL"; exit 1 ;;
  *)          echo "TRIAGE_LLM_FAIL:request_error endpoint=$BASE model=$MODEL"; exit 1 ;;
esac

# The real contract: a parseable JSON verdict with the required keys (not just
# non-empty text). This is the assertion the old probe was missing.
verdict_ok="$(printf '%s' "$content" | python3 -c '
import sys, re, json
t = sys.stdin.read()
t = re.sub(r"<think>.*?</think>", "", t, flags=re.S)
m = re.search(r"\{.*\}", t, re.S)
if not m:
    print("no_json"); sys.exit(0)
try:
    v = json.loads(m.group(0))
except Exception:
    print("bad_json"); sys.exit(0)
need = {"diagnosis","likely_cause","suggested_fix_commands","confidence","escalate"}
print("ok" if need <= set(v) else "missing_keys")
' 2>/dev/null)"

if [ "$verdict_ok" = ok ]; then
  echo "TRIAGE_LLM_OK endpoint=$BASE model=$MODEL max_tokens=$MAX_TOKENS"; exit 0
else
  echo "TRIAGE_LLM_FAIL:${verdict_ok:-empty_content} endpoint=$BASE model=$MODEL max_tokens=$MAX_TOKENS"; exit 1
fi
