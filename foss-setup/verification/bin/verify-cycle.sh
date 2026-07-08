#!/usr/bin/env bash
# systemd entrypoint: run checks, then LLM triage if anything failed.
# Exit code mirrors run-checks (nonzero on crit failures) so the unit state
# reflects fleet health.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${VERIFICATION_STATE_DIR:-/var/lib/verification}"

rc=0
"${SCRIPT_DIR}/run-checks.sh" || rc=$?

failed=$(python3 -c "import json;print(json.load(open('${STATE_DIR}/results.json'))['summary']['failed'])" 2>/dev/null || echo 0)
if [ "${failed}" -gt 0 ]; then
  "${SCRIPT_DIR}/llm-triage.sh" || echo "llm-triage failed (non-fatal)" >&2
fi
exit "${rc}"
