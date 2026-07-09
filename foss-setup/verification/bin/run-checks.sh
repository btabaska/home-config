#!/usr/bin/env bash
# verify-02: run all enabled checks. Thin bash entrypoint; the YAML parsing and
# orchestration live in checks_runner.py (python3 + PyYAML, both verified on mini).
# Usage: run-checks.sh [--host mini|nas|rig|url|<domain>] [--json] [--no-notify]
set -euo pipefail

# Root-guard (audit 2026-07-09): the ssh-based checks (nas-ssh, restic-snapshot-fresh-rig,
# etc.) resolve host aliases + known_hosts from the SERVICE user's ~/.ssh (btabaska). Run as
# root, they FALSELY fail with "Host key verification failed" / "Could not resolve hostname",
# which reads as a NAS/rig outage that isn't real. verification.service runs as User=btabaska;
# match that. Warn (don't hard-fail) so a deliberate root run is still possible.
if [[ "${EUID:-$(id -u)}" -eq 0 && "${VERIFY_ALLOW_ROOT:-0}" != "1" ]]; then
  echo "WARN: run-checks.sh is running as root — ssh-based checks (nas/rig) will FALSELY fail" >&2
  echo "      (root lacks the service user's known_hosts/ssh aliases). Run as btabaska, or set" >&2
  echo "      VERIFY_ALLOW_ROOT=1 to silence. Continuing…" >&2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/checks_runner.py" "$@"
