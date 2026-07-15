#!/usr/bin/env bash
# verify-04: LLM triage of failed checks against the local model on the rig.
# The rig runs 24/7, so the LLM endpoint being down means the rig is down —
# an incident. Recovery path: attempt WoL, wait up to 90s, then hand off to
# llm_triage.py (fresh single-turn completion per failed check).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${VERIFICATION_STATE_DIR:-/var/lib/verification}"
ENV_FILE="${VERIFICATION_ENV_FILE:-/etc/verification/env}"
[ -r "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a

# Endpoint priority: env LLM_BASE_URL, then llama-swap on the rig (ai-01:
# the old ollama :11434 is now a 3-small-model compat shim for HA/Obsidian —
# big models live behind llama-swap :9292, same open no-auth LAN posture;
# litellm :4000 requires an API key so it is not the default).
LLM_BASE_URL="${LLM_BASE_URL:-http://cachyos.tailb31641.ts.net:9292/v1}"
export LLM_BASE_URL
export LLM_MODEL="${LLM_MODEL:-qwen3.6-35b-a3b}"

RIG_MAC="50:eb:f6:b5:82:c6"
RIG_BCAST="192.168.10.255"
TRIAGE_FILE="${STATE_DIR}/triage-$(date +%F).md"

llm_up() { curl -s -m 4 -o /dev/null "${LLM_BASE_URL}/models"; }

if ! llm_up; then
  echo "LLM endpoint ${LLM_BASE_URL} down — rig should be 24/7, this is an incident; attempting WoL recovery" >&2
  # recovery path: prefer the repo's wake-rig helper if installed on mini, else embedded WoL
  if [ -x /opt/foss-setup/scripts/gaming/wake-rig.sh ]; then
    RIG_MAC="$RIG_MAC" /opt/foss-setup/scripts/gaming/wake-rig.sh || true
  else
    wakeonlan -i "$RIG_BCAST" "$RIG_MAC" >/dev/null
  fi
  waited=0
  until llm_up; do
    sleep 5; waited=$((waited + 5))
    if [ "$waited" -ge 90 ]; then
      mkdir -p "$STATE_DIR"
      printf '\n## %s\n\nINCIDENT: rig unavailable — LLM endpoint %s did not answer within 90s after WoL recovery attempt (rig is expected 24/7); triage skipped.\n' \
        "$(date -Is)" "$LLM_BASE_URL" >> "$TRIAGE_FILE"
      echo "INCIDENT: rig unavailable after WoL recovery attempt — triage skipped (recorded in ${TRIAGE_FILE})" >&2
      exit 0
    fi
  done
  echo "rig up after ${waited}s" >&2
fi

exec python3 "${SCRIPT_DIR}/llm_triage.py" "$@"
