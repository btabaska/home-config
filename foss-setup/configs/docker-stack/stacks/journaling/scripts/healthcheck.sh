#!/usr/bin/env bash
# journaling stack healthcheck (journal-01) — run on the mini.
# Curls all three local services + the rig llama-swap inference endpoint the
# journal-analyze workflow depends on. Exit non-zero if any probe fails.
#
#   ssh mini 'cd /opt/stacks/journaling && ./scripts/healthcheck.sh'
set -uo pipefail

RIG_IP="${RIG_IP:-192.168.10.12}"
fail=0

check() {
  local name="$1" url="$2" want="$3"
  local code
  code="$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$url" 2>/dev/null || echo 000)"
  if [[ "$code" =~ $want ]]; then
    printf 'OK    %-14s %-46s (%s)\n' "$name" "$url" "$code"
  else
    printf 'FAIL  %-14s %-46s (%s, want %s)\n' "$name" "$url" "$code" "$want"
    fail=1
  fi
}

check memos    "http://localhost:5230/healthz"          '^200$'
check n8n      "http://localhost:5678/healthz"          '^200$'
check whisper  "http://localhost:8010/health"           '^200$'
check rig-llm  "http://${RIG_IP}:9292/v1/models"        '^200$'

if [[ $fail -eq 0 ]]; then
  echo "journaling: all healthy"
else
  echo "journaling: DEGRADED"
fi
exit $fail
