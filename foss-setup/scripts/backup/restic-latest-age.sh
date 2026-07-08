#!/usr/bin/env bash
#
# restic-latest-age.sh — print freshness of the newest restic snapshot for this
# host. Deployed to /usr/local/bin/restic-latest-age (root, 0755).
#
# WHY IT EXISTS: the verification runner executes as btabaska, but the restic
# env file (/etc/restic/env) is root-only 0600. Rather than loosening the env
# file's permissions, a single sudoers rule (/etc/sudoers.d/verification-restic)
# lets btabaska run EXACTLY this root-owned script with no arguments:
#   btabaska ALL=(root) NOPASSWD: /usr/local/bin/restic-latest-age
# The verification check is then just: sudo -n /usr/local/bin/restic-latest-age
#
# Output:  "FRESH age_hours=N latest=<timestamp>"  exit 0   (age < MAX_AGE_HOURS)
#          "STALE age_hours=N latest=<timestamp>"  exit 1
#          "NO-SNAPSHOTS"                          exit 1
# MAX_AGE_HOURS defaults to 26 (daily timer + slack); env-overridable, NOT an
# argv argument — sudoers pins the zero-argument invocation.

set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/restic/env}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-26}"

[[ -r "${ENV_FILE}" ]] || { echo "ERROR: cannot read ${ENV_FILE} (run via sudo)" >&2; exit 2; }
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

# No `latest` positional (older restic quirks); retention keeps the list small
# and the python takes the newest timestamp anyway.
restic snapshots --host "$(hostname -s)" --json 2>/dev/null | python3 -c '
import json, re, sys
from datetime import datetime, timezone

raw_in = sys.stdin.read().strip()
if not raw_in:
    print("ERROR restic snapshots produced no output (creds? network?)")
    sys.exit(2)
snaps = json.loads(raw_in) or []
if not snaps:
    print("NO-SNAPSHOTS")
    sys.exit(1)
raw = max(s["time"] for s in snaps)
# restic emits RFC3339 with up to nanosecond precision and sometimes a "Z"
# suffix; trim to microseconds and use +00:00 so fromisoformat copes on any
# python3 (3.10 rejects the bare Z).
clean = re.sub(r"\.(\d{6})\d*", r".\1", raw).replace("Z", "+00:00")
t = datetime.fromisoformat(clean)
age_h = (datetime.now(timezone.utc) - t).total_seconds() / 3600
state = "FRESH" if age_h < float(sys.argv[1]) else "STALE"
print(f"{state} age_hours={age_h:.1f} latest={raw}")
sys.exit(0 if state == "FRESH" else 1)
' "${MAX_AGE_HOURS}"
