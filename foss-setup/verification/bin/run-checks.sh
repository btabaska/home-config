#!/usr/bin/env bash
# verify-02: run all enabled checks. Thin bash entrypoint; the YAML parsing and
# orchestration live in checks_runner.py (python3 + PyYAML, both verified on mini).
# Usage: run-checks.sh [--host mini|nas|rig|url|<domain>] [--json] [--no-notify]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/checks_runner.py" "$@"
