#!/usr/bin/env bash
# verify-02: run all enabled checks. Thin bash entrypoint; the YAML parsing and
# orchestration live in checks_runner.py (python3 + PyYAML, both verified on mini).
# Usage: run-checks.sh [--host mini|nas|rig|url|<domain>] [--json] [--no-notify]
set -euo pipefail

# Root-guard (audit 2026-07-09, hardened 2026-07-10): the ssh-based checks (nas-ssh,
# restic-snapshot-fresh-rig, etc.) resolve host aliases + known_hosts from the SERVICE
# user's ~/.ssh (btabaska). Run as root, they FALSELY fail with "Host key verification
# failed", which reads as a NAS/rig outage that isn't real. The old warn-and-continue
# paged a fake 14-failure/3-crit outage on 2026-07-10 AND poisoned the results.json
# state diff — so now we refuse outright. verification.service runs as User=btabaska.
if [[ "${EUID:-$(id -u)}" -eq 0 && "${VERIFY_ALLOW_ROOT:-0}" != "1" ]]; then
  echo "ERROR: refusing to run as root — ssh-based checks (nas/rig) FALSELY fail and page" >&2
  echo "       a fake outage, and the garbage run poisons the notify state diff." >&2
  echo "       Run as btabaska (like verification.service), or set VERIFY_ALLOW_ROOT=1" >&2
  echo "       for a deliberate root run. No checks were run, nothing was notified." >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/checks_runner.py" "$@"
