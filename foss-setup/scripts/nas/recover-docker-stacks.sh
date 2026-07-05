#!/usr/bin/env bash
# Recover Synology Container Manager + NAS compose stacks after dockerd crash.
# Thin wrapper — delegates to nas-docker-health.sh (full stack + port checks).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/nas-docker-health.sh" "$@"
