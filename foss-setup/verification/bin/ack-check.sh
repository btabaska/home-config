#!/usr/bin/env bash
# Acknowledge a failing verification check: it keeps RUNNING and being recorded
# in results.json / summaries, but stops paging ntfy until the ack expires.
# For known/accepted outages (e.g. playit upstream 2026-07-10) so the sweep
# doesn't flap-page what the operator already knows. State: acks.json in
# VERIFICATION_STATE_DIR (default /var/lib/verification) — same dir the runner
# uses, so run this as btabaska on mini like the runner itself.
#
# Usage:
#   ack-check.sh <check-id> <hours> [reason...]   # add/refresh an ack
#   ack-check.sh --list                            # show live acks
#   ack-check.sh --clear <check-id>                # remove an ack early
set -euo pipefail

STATE_DIR="${VERIFICATION_STATE_DIR:-/var/lib/verification}"
ACKS="${STATE_DIR}/acks.json"

case "${1:-}" in
  --list)
    python3 - "$ACKS" <<'EOF'
import json, sys, datetime
try:
    acks = json.load(open(sys.argv[1]))
except Exception:
    acks = {}
now = datetime.datetime.now().astimezone()
if not acks:
    print("no acks")
for cid, m in sorted(acks.items()):
    live = "LIVE" if datetime.datetime.fromisoformat(m["until"]) > now else "expired"
    print(f"{live:8} {cid}  until {m['until'][:16]}  — {m.get('reason','')}")
EOF
    ;;
  --clear)
    [ -n "${2:-}" ] || { echo "usage: ack-check.sh --clear <check-id>" >&2; exit 1; }
    python3 - "$ACKS" "$2" <<'EOF'
import json, sys
path, cid = sys.argv[1], sys.argv[2]
try:
    acks = json.load(open(path))
except Exception:
    acks = {}
if acks.pop(cid, None) is None:
    print(f"no ack for {cid}")
else:
    json.dump(acks, open(path, "w"), indent=2)
    print(f"cleared ack: {cid}")
EOF
    ;;
  ""|--help|-h)
    grep '^#' "$0" | sed 's/^# \{0,1\}//' | head -12
    ;;
  *)
    CID="$1"; HOURS="${2:?usage: ack-check.sh <check-id> <hours> [reason...]}"
    shift 2; REASON="${*:-}"
    python3 - "$ACKS" "$CID" "$HOURS" "$REASON" <<'EOF'
import json, sys, datetime
path, cid, hours, reason = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
try:
    acks = json.load(open(path))
except Exception:
    acks = {}
until = (datetime.datetime.now().astimezone()
         + datetime.timedelta(hours=hours)).isoformat(timespec="seconds")
acks[cid] = {"until": until, "reason": reason}
json.dump(acks, open(path, "w"), indent=2)
print(f"acked {cid} until {until}" + (f" — {reason}" if reason else ""))
EOF
    ;;
esac
